from __future__ import annotations

import uuid
from typing import Any

from ..datasets.models import Dataset
from ..datasets.repository import DatasetRepository
from ..planner.service import PlannerService
from ..profiling.schemas import DatasetContext
from ..profiling.service import DatasetContextService
from ..results.models import AnalysisResult as AnalysisResultModel
from ..results.repository import ResultsRepository
from ..visualization.service import VisualizationService
from ...orchestration.error_contract import public_message_for_stage
from .processor import AnalysisProcessor
from .run_service import AnalysisRunService, build_deterministic_analysis_code
from .sandbox import AnalysisSandbox
from .schemas import (
    AnalysisError,
    AnalysisExecutionResult,
    AnalysisPlan,
    ColumnGroundingResult,
    FinalStatus,
    MetadataSnapshot,
    QuestionUnderstanding,
)


class AnalysisService:
    """Thin orchestration layer for the analysis pipeline."""

    def __init__(
        self,
        *,
        dataset_repository: DatasetRepository,
        dataset_context_service: DatasetContextService,
        planner_service: PlannerService,
        run_service: AnalysisRunService,
        processor: AnalysisProcessor,
        sandbox: AnalysisSandbox,
        results_repository: ResultsRepository | None = None,
        visualization_service: VisualizationService | None = None,
        max_retries: int = 1,
    ) -> None:
        self.dataset_repository = dataset_repository
        self.dataset_context_service = dataset_context_service
        self.planner_service = planner_service
        self.run_service = run_service
        self.processor = processor
        self.sandbox = sandbox
        self.results_repository = results_repository
        self.visualization_service = visualization_service
        self.max_retries = max_retries

    # profiling 기반 dataset_context를 내부 MetadataSnapshot 호환 shape로 변환한다.
    def build_dataset_metadata(self, source_id: str) -> MetadataSnapshot:
        dataset_context = self.dataset_context_service.build_context(source_id)
        if not dataset_context.available:
            raise FileNotFoundError(f"dataset context unavailable: {source_id}")
        return self._build_metadata_snapshot(dataset_context)

    # analysis 전체 상위 흐름을 조합한다.
    # 질문 해석, plan 생성/검증, 코드 생성/실행, 시각화 연계를 순서대로 수행한다.
    def run(
        self,
        *,
        question: str,
        source_id: str,
        session_id: str | None = None,
        request_context: str | None = None,
        guideline_context: dict[str, Any] | None = None,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        dataset = self._get_dataset(source_id)
        if dataset is None:
            raise FileNotFoundError(f"dataset not found: {source_id}")
        dataset_context = self.dataset_context_service.build_context(source_id)
        if not dataset_context.available:
            raise FileNotFoundError(f"dataset context unavailable: {source_id}")

        planning_result = self.planner_service.plan(
            user_input=question,
            request_context=request_context,
            source_id=source_id,
            dataset_context=dataset_context,
            guideline_context=guideline_context,
            model_id=model_id,
        )
        if planning_result.needs_clarification:
            return {
                "planning_result": planning_result,
                "dataset_meta": None,
                "question_understanding": None,
                "column_grounding": None,
                "analysis_plan_draft": None,
                "analysis_plan": None,
                "analysis_result": None,
                "analysis_error": None,
                "final_status": "needs_clarification",
                "clarification_question": planning_result.clarification_question,
                "analysis_result_id": None,
                "visualization_output": None,
            }
        if planning_result.route != "analysis" or planning_result.analysis_plan is None:
            raise ValueError("planner did not route this request to analysis")

        analysis_plan = planning_result.analysis_plan
        dataset_meta = analysis_plan.metadata_snapshot

        execution_bundle = self._run_code_generation_loop(
            question=question,
            dataset=dataset,
            analysis_plan=analysis_plan,
            model_id=model_id,
        )

        visualization_output = None
        result_id = None
        if execution_bundle["final_status"] == "success":
            visualization_output = self._build_visualization_output(
                source_id=source_id,
                analysis_plan=analysis_plan,
                execution_result=execution_bundle["analysis_result"],
            )
            result_id = self._persist_result(
                question=question,
                source_id=source_id,
                session_id=session_id,
                analysis_plan=analysis_plan,
                generated_code=execution_bundle.get("generated_code"),
                execution_result=execution_bundle["analysis_result"],
            )

        return {
            "planning_result": planning_result,
            "dataset_meta": dataset_meta,
            "question_understanding": None,
            "column_grounding": None,
            "analysis_plan_draft": None,
            "analysis_plan": analysis_plan,
            "generated_code": execution_bundle.get("generated_code"),
            "validated_code": execution_bundle.get("validated_code"),
            "sandbox_result": execution_bundle.get("sandbox_result"),
            "analysis_result": execution_bundle["analysis_result"],
            "analysis_error": execution_bundle.get("analysis_error"),
            "final_status": execution_bundle["final_status"],
            "analysis_result_id": result_id,
            "visualization_output": visualization_output,
        }

    # 코드 생성 -> 코드 검증 -> snadbox 실행 -> 결과 검증을 수행하고 실패 시 제한된 횟수만큼 code repair를 재시도한다.
    def _run_code_generation_loop(
        self,
        *,
        question: str,
        dataset: Dataset,
        analysis_plan: AnalysisPlan,
        model_id: str | None,
    ) -> dict[str, Any]:
        generated_code = ""
        validated_code = ""
        sandbox_result = None
        analysis_error = None
        deterministic_fallback_attempted = False
        execution_result = AnalysisExecutionResult(
            execution_status="fail",
            error_stage="code_generation",
            error_message="analysis execution did not start",
        )
        deterministic_bundle = self._try_deterministic_fallback(
            dataset=dataset,
            analysis_plan=analysis_plan,
            attempt=0,
            trigger_stage="deterministic_codegen",
            original_execution_result=None,
        )
        if deterministic_bundle is not None:
            return deterministic_bundle

        for attempt in range(self.max_retries + 1):
            try:
                # 첫 시도에서는 plan 기반으로 신규 분석 코드를 생성한다.
                if attempt == 0:
                    generated_code = self.run_service.generate_analysis_code(
                        question=question,
                        analysis_plan=analysis_plan,
                        model_id=model_id,
                    )
                # 실패 이후에는 이전 코드와 에러를 반영해 코드만 수정한다.
                else:
                    if analysis_error is None:
                        analysis_error = self.processor.build_error(
                            "code_generation",
                            "analysis execution failed",
                            detail={"attempt": attempt},
                        )
                    generated_code = self.run_service.repair_analysis_code(
                        question=question,
                        analysis_plan=analysis_plan,
                        previous_code=generated_code,
                        analysis_error=analysis_error,
                        model_id=model_id,
                    )
                validated_code = self.processor.validate_generated_code(
                    generated_code=generated_code,
                    analysis_plan=analysis_plan,
                )
                sandbox_result = self.sandbox.execute(
                    code=validated_code,
                    dataset_path=str(dataset.storage_path),
                )
                execution_result = self.processor.validate_execution_result(
                    sandbox_result=sandbox_result,
                    analysis_plan=analysis_plan,
                )
                if execution_result.execution_status == "success":
                    return {
                        "generated_code": generated_code,
                        "validated_code": validated_code,
                        "sandbox_result": sandbox_result,
                        "analysis_result": execution_result,
                        "analysis_error": None,
                        "final_status": "success",
                        "retry_count": attempt,
                        "deterministic_fallback_used": False,
                    }

                if not deterministic_fallback_attempted:
                    deterministic_fallback_attempted = True
                    fallback_bundle = self._try_deterministic_fallback(
                        dataset=dataset,
                        analysis_plan=analysis_plan,
                        attempt=attempt,
                        trigger_stage=execution_result.error_stage or "result_validation",
                        original_execution_result=execution_result,
                    )
                    if fallback_bundle is not None:
                        return fallback_bundle

                analysis_error = self.processor.build_error(
                    execution_result.error_stage or "result_validation",
                    execution_result.error_message or "analysis execution failed",
                    detail=self._build_analysis_error_detail(
                        attempt=attempt + 1,
                        execution_result=execution_result,
                        analysis_plan=analysis_plan,
                        trigger_stage=execution_result.error_stage,
                    ),
                )
            except Exception as exc:
                stage = "code_generation" if not generated_code else "code_validation"
                if stage == "code_validation" and not deterministic_fallback_attempted:
                    deterministic_fallback_attempted = True
                    fallback_bundle = self._try_deterministic_fallback(
                        dataset=dataset,
                        analysis_plan=analysis_plan,
                        attempt=attempt,
                        trigger_stage=stage,
                        original_execution_result=execution_result,
                        allow_failed_bundle=False,
                    )
                    if fallback_bundle is not None:
                        return fallback_bundle
                safe_message = public_message_for_stage(stage)
                diagnostic_message = f"{type(exc).__name__}: {exc}"
                detail: dict[str, Any] = {
                    "attempt": attempt + 1,
                    "exception_type": type(exc).__name__,
                    "diagnostic_message": diagnostic_message,
                }
                if stage == "code_validation":
                    detail["internal_stage"] = stage
                analysis_error = self.processor.build_error(
                    stage,
                    safe_message,
                    detail=detail,
                )
                execution_result = AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                    diagnostic_message=diagnostic_message,
                    quality_status="invalid",
                    quality_reason=analysis_error.message,
                )

        return {
            "generated_code": generated_code,
            "validated_code": validated_code,
            "sandbox_result": sandbox_result,
            "analysis_result": execution_result,
            "analysis_error": analysis_error,
            "final_status": "fail",
            "retry_count": self.max_retries,
            "deterministic_fallback_used": False,
        }

    def _try_deterministic_fallback(
        self,
        *,
        dataset: Dataset,
        analysis_plan: AnalysisPlan,
        attempt: int,
        trigger_stage: str,
        original_execution_result: AnalysisExecutionResult | None = None,
        allow_failed_bundle: bool = True,
    ) -> dict[str, Any] | None:
        fallback_code = build_deterministic_analysis_code(analysis_plan)
        if not fallback_code:
            return None
        try:
            validated_code = self.processor.validate_generated_code(
                generated_code=fallback_code,
                analysis_plan=analysis_plan,
            )
            sandbox_result = self.sandbox.execute(
                code=validated_code,
                dataset_path=str(dataset.storage_path),
            )
            execution_result = self.processor.validate_execution_result(
                sandbox_result=sandbox_result,
                analysis_plan=analysis_plan,
            )
        except (OSError, ValueError):
            return None

        if execution_result.execution_status == "success":
            return {
                "generated_code": fallback_code,
                "validated_code": validated_code,
                "sandbox_result": sandbox_result,
                "analysis_result": execution_result,
                "analysis_error": None,
                "final_status": "success",
                "retry_count": attempt,
                "deterministic_fallback_used": True,
                "deterministic_fallback_attempted": True,
                "fallback_trigger_stage": trigger_stage,
            }

        if not allow_failed_bundle:
            return None

        analysis_error = self.processor.build_error(
            execution_result.error_stage or "result_validation",
            execution_result.error_message or "analysis execution failed",
            detail=self._build_analysis_error_detail(
                attempt=attempt + 1,
                execution_result=execution_result,
                analysis_plan=analysis_plan,
                trigger_stage=trigger_stage,
                original_execution_result=original_execution_result,
            ),
        )
        return {
            "generated_code": fallback_code,
            "validated_code": validated_code,
            "sandbox_result": sandbox_result,
            "analysis_result": execution_result,
            "analysis_error": analysis_error,
            "final_status": "fail",
            "retry_count": attempt,
            "deterministic_fallback_used": True,
            "deterministic_fallback_attempted": True,
            "fallback_trigger_stage": trigger_stage,
        }

    @staticmethod
    def _build_analysis_error_detail(
        *,
        attempt: int,
        execution_result: AnalysisExecutionResult,
        analysis_plan: AnalysisPlan | None = None,
        trigger_stage: str | None = None,
        original_execution_result: AnalysisExecutionResult | None = None,
    ) -> dict[str, Any]:
        detail: dict[str, Any] = {"attempt": attempt}
        if trigger_stage:
            detail["fallback_trigger_stage"] = trigger_stage
        if execution_result.quality_status:
            detail["quality_status"] = execution_result.quality_status
        if execution_result.quality_reason:
            detail["quality_reason"] = execution_result.quality_reason
        if execution_result.diagnostic_message:
            detail["diagnostic_message"] = execution_result.diagnostic_message
        if original_execution_result and original_execution_result.error_stage:
            detail["original_internal_stage"] = original_execution_result.error_stage
        if execution_result.warnings:
            detail["warnings"] = [
                warning.model_dump() for warning in execution_result.warnings
            ]
        if analysis_plan is not None:
            detail.update(_build_safe_failure_context(analysis_plan, execution_result))
        return detail

    # 질문이나 plan 초안이 모호할 때 needs_clarification 응답 payload를 만든다.
    def _build_clarification_response(
        self,
        *,
        question_understanding: QuestionUnderstanding,
        dataset_meta: MetadataSnapshot,
        column_grounding: ColumnGroundingResult | None = None,
        plan_draft: Any | None = None,
    ) -> dict[str, Any]:
        return {
            "dataset_meta": dataset_meta,
            "question_understanding": question_understanding,
            "column_grounding": column_grounding,
            "analysis_plan_draft": plan_draft,
            "analysis_plan": None,
            "analysis_result": None,
            "analysis_error": None,
            "final_status": "needs_clarification",
            "clarification_message": question_understanding.clarification_message
            or getattr(plan_draft, "clarification_message", ""),
            "analysis_result_id": None,
            "visualization_output": None,
        }

    # analysis 결과를 visualization 입력으로 넘겨 후처리 결과를 만든다.
    def _build_visualization_output(
        self,
        *,
        source_id: str,
        analysis_plan: AnalysisPlan,
        execution_result: AnalysisExecutionResult,
    ) -> Any | None:
        if self.visualization_service is None:
            return None
        build_method = getattr(
            self.visualization_service, "build_from_analysis_result", None
        )
        if callable(build_method):
            return build_method(
                source_id=source_id,
                analysis_plan=analysis_plan,
                analysis_result=execution_result,
            )
        return None

    # 결과 저장소가 준비되어 있으면 analysis 결과를 저장하고 result id를 반환한다.
    def _persist_result(
        self,
        *,
        question: str,
        source_id: str,
        session_id: str | None,
        analysis_plan: AnalysisPlan | None,
        generated_code: str | None,
        execution_result: AnalysisExecutionResult,
    ) -> str | None:
        if self.results_repository is None:
            return None

        create_method = getattr(self.results_repository, "create_analysis_result", None)
        if callable(create_method):
            persisted = create_method(
                question=question,
                source_id=source_id,
                session_id=session_id,
                analysis_plan=analysis_plan,
                generated_code=generated_code,
                execution_result=execution_result,
            )
            return getattr(persisted, "id", None)

        db = getattr(self.results_repository, "db", None)
        if db is None:
            return None
        # 최소 실행 결과를 JSON 형태로 저장한다.
        record = AnalysisResultModel(
            id=str(uuid.uuid4()),
            data_json={
                "question": question,
                "source_id": source_id,
                "session_id": session_id,
                "analysis_plan": analysis_plan.model_dump() if analysis_plan else None,
                "generated_code": generated_code,
                "analysis_result": execution_result.model_dump(),
            },
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return str(record.id)

    def _get_dataset(self, source_id: str) -> Dataset | None:
        return self.dataset_repository.get_by_source_id(source_id)

    @staticmethod
    def _build_metadata_snapshot(dataset_context: DatasetContext) -> MetadataSnapshot:
        return MetadataSnapshot(
            columns=dataset_context.columns,
            dtypes=dataset_context.dtypes,
            numeric_columns=dataset_context.numeric_columns,
            datetime_columns=dataset_context.datetime_columns,
            categorical_columns=dataset_context.categorical_columns,
            row_count=dataset_context.row_count_total,
        )


def _build_safe_failure_context(
    analysis_plan: AnalysisPlan,
    execution_result: AnalysisExecutionResult,
) -> dict[str, str]:
    failed_column = _infer_failed_column(analysis_plan)
    reason_summary = _safe_reason_summary(execution_result)
    return {
        "internal_stage": execution_result.error_stage or "result_validation",
        "failed_column": failed_column,
        "operation": _infer_operation(analysis_plan),
        "reason_summary": reason_summary,
        "suggested_action": _suggested_action(failed_column, reason_summary),
    }


def _infer_failed_column(analysis_plan: AnalysisPlan) -> str:
    if _infer_operation(analysis_plan) == "numeric outlier detection":
        for metric in analysis_plan.metrics:
            if (
                metric.column
                and "outlier_target" in f"{metric.name} {metric.alias}".lower()
            ):
                return metric.column
        for metric in analysis_plan.metrics:
            if metric.column and _column_is_named_in_plan(analysis_plan, metric.column):
                return metric.column
    numeric_columns = set(analysis_plan.metadata_snapshot.numeric_columns)
    for metric in analysis_plan.metrics:
        if metric.column and metric.column in numeric_columns:
            return metric.column
    for column in analysis_plan.used_columns:
        if column in numeric_columns:
            return column
    return analysis_plan.used_columns[0] if analysis_plan.used_columns else "분석 대상 컬럼"


def _column_is_named_in_plan(analysis_plan: AnalysisPlan, column: str) -> bool:
    haystack = f"{analysis_plan.analysis_type} {analysis_plan.objective}".lower()
    return column.lower() in haystack


def _infer_operation(analysis_plan: AnalysisPlan) -> str:
    haystack = f"{analysis_plan.analysis_type} {analysis_plan.objective}".lower()
    if any(token in haystack for token in ("outlier", "anomaly", "이상치")):
        return "numeric outlier detection"
    if analysis_plan.metrics:
        return "analysis metric calculation"
    return "analysis execution"


def _safe_reason_summary(execution_result: AnalysisExecutionResult) -> str:
    reason = (
        execution_result.error_message
        or execution_result.quality_reason
        or "analysis result did not satisfy the expected output contract"
    )
    if reason == "outlier information is required":
        return "이상치 분석 결과에 필요한 outliers 지표가 없습니다."
    if reason == "target column has no numeric values for outlier detection":
        return "대상 컬럼에 이상치 계산에 사용할 수 있는 숫자 값이 없습니다."
    if reason == "analysis execution failed":
        return "분석 코드 실행이 완료되지 않았습니다."
    return str(reason)[:240]


def _suggested_action(failed_column: str, reason_summary: str) -> str:
    if "숫자" in reason_summary or "numeric" in reason_summary:
        return f"{failed_column} 컬럼의 숫자 형식과 결측값을 확인해 주세요."
    if "outlier" in reason_summary or "이상치" in reason_summary:
        return (
            f"{failed_column} 컬럼을 기준으로 이상치 지표가 생성되도록 "
            "질문 범위나 기준 컬럼을 줄여 다시 실행해 주세요."
        )
    return (
        f"{failed_column} 컬럼의 값과 분석 기준을 확인한 뒤 "
        "질문 범위를 좁혀 다시 실행해 주세요."
    )
