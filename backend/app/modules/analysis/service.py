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
from .processor import AnalysisProcessor
from .run_service import AnalysisRunService
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
        execution_result = AnalysisExecutionResult(
            execution_status="fail",
            error_stage="code_generation",
            error_message="analysis execution did not start",
        )
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
                    dataset_path=dataset.storage_path,
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
                    }

                analysis_error = self.processor.build_error(
                    execution_result.error_stage or "result_validation",
                    execution_result.error_message or "analysis execution failed",
                    detail={"attempt": attempt + 1},
                )
            except Exception as exc:
                stage = "code_generation" if not generated_code else "code_validation"
                analysis_error = self.processor.build_error(
                    stage,
                    str(exc),
                    detail={
                        "attempt": attempt + 1,
                        "exception_type": type(exc).__name__,
                    },
                )
                execution_result = AnalysisExecutionResult(
                    execution_status="fail",
                    error_stage=analysis_error.stage,
                    error_message=analysis_error.message,
                )

        return {
            "generated_code": generated_code,
            "validated_code": validated_code,
            "sandbox_result": sandbox_result,
            "analysis_result": execution_result,
            "analysis_error": analysis_error,
            "final_status": "fail",
        }

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
