from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any, Mapping, Protocol

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from ...core.ai import LLMGateway, PromptRegistry
from ..analysis.processor import AnalysisProcessor
from ..analysis.schemas import (
    AnalysisPlan,
    AnalysisPlanDraft,
    ExpectedOutputSpec,
    FilterCondition,
    MetadataSnapshot,
    MetricSpec,
    QuestionUnderstanding,
    SortSpec,
    TimeContext,
    VisualizationHint,
)
from ..profiling.schemas import DatasetContext
from ..profiling.prompt_context import trim_fast_path_bulk_context_fields
from .query_validation import (
    find_explicit_column_issue,
    should_preflight_explicit_column_issue,
)
from .schemas import PlannerDecision, PlanningResult, PlanningRoute

_EXACT_COLUMN_RE = re.compile(r"[`'\"]([^`'\"]+)[`'\"]")
_OUTLIER_INTENT_TERMS = ("이상치", "outlier", "anomaly", "abnormal")
_ROOT_CAUSE_INTENT_TERMS = ("원인", "cause", "reason")
_VISUALIZATION_INTENT_TERMS = ("시각화", "그래프", "차트", "visualize", "chart", "graph")
_REPORT_INTENT_TERMS = ("리포트", "보고서", "report")
_QUALITY_SUMMARY_INTENT_TERMS = (
    "전체 품질 현황",
    "품질 현황",
    "품질",
    "양품",
    "불량 비율",
    "불량 사유",
    "quality",
)
_PRODUCT_COUNT_INTENT_TERMS = (
    "생산량",
    "production",
    "count",
    "건수",
)


class DatasetContextProvider(Protocol):
    def build_context(
        self,
        source_id: str,
        *,
        include_ai_aliases: bool | None = None,
    ) -> DatasetContext: ...


PROMPTS = PromptRegistry(
    {
        "decision.system": (
            "너는 데이터 질문 planner다. "
            "입력은 user_input, request_context, dataset_context, guideline_context다. "
            "반드시 PlannerDecision 스키마로만 반환하라. "
            "is_general_question은 선택된 dataset와 무관한 일반 상식 질문, 잡담, 도구 사용 질문처럼 "
            "dataset 경로를 타지 말아야 할 때만 true다. "
            "dataset 설명, 컬럼 소개, 샘플 확인, 파일 내용 확인처럼 dataset 자체를 묻는 질문이면 is_general_question을 false로 두고 ask_analysis도 false로 둬 fallback_rag로 보내라. "
            "ask_analysis는 정량 계산, 합계, 평균, 그룹화, 비교, 추세, 상관 분석, 관계 분석, 데이터 기반 시각화, 데이터 기반 리포트 요청이면 true다. "
            "단순한 dataset 설명, 컬럼 소개, 샘플 확인, 비정량적 문서형 질의응답이면 ask_analysis를 false로 둘 수 있다. "
            "preprocess_required는 결측치 처리, 형변환, 문자열 정리, 정규화, 스케일링, 인코딩, 컬럼명 변경, 파생 컬럼 생성처럼 "
            "데이터를 먼저 정제하거나 변환해야 할 때만 true다. "
            "사용자가 분석 전에 필요한 전처리 확인, 전처리 계획, 전처리 적용만 요청하고 전처리 이후의 계산/집계/차트/리포트를 요청하지 않았다면 "
            "preprocess_required=true, ask_analysis=false로 둬라. "
            "사용자가 전처리 후 분석/시각화/리포트까지 명시하면 preprocess_required=true와 함께 해당 downstream 플래그도 true로 둬라. "
            "월/주/일 버킷팅, 최근 N개월 필터링, 집계, 비교, 추세 분석은 전처리가 아니라 분석이므로 그 이유만으로 preprocess_required를 true로 두지 마라. "
            "양품/불량 비율, 사유별 건수, 제품별 생산량, 그룹별 count, 차트/그래프/시각화 요청은 원본 컬럼으로 계산 가능한 분석/시각화다. "
            "사용자가 결측치 처리, 정규화, 표준화, 인코딩, 형변환 같은 전처리를 명시하지 않았다면 이런 요청은 preprocess_required=false로 둬라. "
            "need_visualization은 사용자가 차트/그래프/시각화를 원하면 true다. "
            "need_report는 리포트/보고서/요약 보고 형식을 원하면 true다. "
            "guideline_context_used는 guideline_context.has_evidence가 true이고, 그 근거가 planning에 실제로 영향을 준 경우에만 true다."
        ),
        "question_understanding.system": (
            "너는 데이터 분석 질문 해석기다. "
            "사용자 질문을 QuestionUnderstanding 스키마로 구조화하라. "
            "guideline_context.semantic_glossary가 있으면 evidence_summary보다 우선 적용하라. "
            "질문이 모호해 보여도 guideline_context.has_evidence가 true이고 "
            "그 근거에 용어, 컬럼, 지표, 공식 매핑이 있으면 먼저 그 근거로 해석하라. "
            "guideline_context로도 해소되지 않는 모호성만 needs_clarification으로 설정하고 clarification_message를 작성하라. "
            "metric_keywords와 group_keywords는 실제 컬럼명이 아니라 질문에서 추출한 개념 중심 키워드로 작성하라. "
            "질문에 3월, 2월, 이번 달처럼 상대적으로 해석 가능한 월/기간 표현이 있고 dataset_meta의 시간 범위 안에서 자연스럽게 해석 가능하면 불필요한 clarification을 만들지 마라."
        ),
        "plan_draft.system": (
            "너는 데이터 분석 플래너다. "
            "입력으로 주어진 질문 해석 결과, 컬럼 grounding 결과, 데이터셋 메타정보, guideline_context를 바탕으로 "
            "AnalysisPlanDraft 스키마 형식으로만 반환하라. "
            "guideline_context.semantic_glossary가 있으면 제품, 불량 지표, 불량값, 불량률 공식의 최우선 근거로 적용하라. "
            "guideline_context.has_evidence가 true이면 먼저 그 근거의 용어, 컬럼, 지표, 공식 매핑을 적용하라. "
            "guideline_context로도 해소되지 않는 모호성만 ambiguity_status를 needs_clarification으로 설정하라. "
            "가이드라인이 0/1 indicator에서 1이 결함/불량이라고 정의하고 불량률을 결함 건수/전체 건수로 설명하면, "
            "그 indicator 컬럼의 avg 또는 rate metric으로 계획하고 positive_value에 1을 넣어라. "
            "전역 filters로 결함 행만 남겨 전체 분모를 제거하지 마라. "
            "metrics는 반드시 최소 1개 이상 포함하라. "
            "결측치 현황, missing value, missing rate, 전처리 계획 요청에서는 "
            "column, columns, column_name, column_names, column_type, data_type, feature_type 같은 "
            "추상 축을 group_by, filters, visualization_hint.x, visualization_hint.series에 넣지 마라. "
            "사용자가 차트나 그래프를 명시적으로 요청하지 않았다면 visualization_hint.preferred_chart는 none으로 두어라. "
            "컬럼별 결측 현황은 실제 컬럼들을 metric으로 열거해서 표현하고, 메타 수준 분류는 summary/objective 설명으로만 다뤄라. "
            "관계 분석(scatter, correlation, relationship) 질문에서는 우선 원본 수치 컬럼 2개를 직접 사용하라. "
            "관계 분석 질문에서는 사용자가 평균, 그룹별 평균, 요약을 명시적으로 요구하지 않았다면 group_by를 기본적으로 비워 두고 원시 행 단위 x/y 포인트를 사용하라. "
            "line, material_type 같은 범주형 컬럼이 있으면 집계 기준으로 쓰기보다 series/color 구분으로 우선 사용하라. "
            "파생 컬럼(derived_columns)은 원본 컬럼만으로 질문에 답할 수 없을 때만 추가하라. "
            "특히 ratio, arithmetic 같은 파생 컬럼은 사용자가 명시적으로 요청하지 않았다면 만들지 마라. "
            "관계 분석 질문에서는 correlation, slope, regression 같은 추가 관계 지표(metric)를 기본적으로 만들지 마라. "
            "사용자가 명시적으로 상관계수나 회귀계수를 요청한 경우가 아니면, 원본 두 컬럼과 scatter 시각화에 필요한 최소 metric만 사용하라. "
            "월별/주별/일별 추세 질문에서는 timestamp/date 컬럼을 분석 단계에서 버킷팅하여 집계하라. 이 때문에 preprocess 파생 컬럼이 필요하다고 가정하지 마라. "
            "라인별 평균 불량률 추세 같은 질문이면 time bucket + series(line) + avg metric 구조로 계획하라."
        ),
    }
)


class PlannerService:
    """Single source of truth for route, clarification, preprocess need, and analysis plans."""

    def __init__(
        self,
        *,
        dataset_context_service: DatasetContextProvider,
        analysis_processor: AnalysisProcessor,
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.dataset_context_service = dataset_context_service
        self.analysis_processor = analysis_processor
        self.default_model = default_model
        self.llm = LLMGateway(default_model=default_model)

    def plan(
        self,
        *,
        user_input: str,
        request_context: str | None,
        source_id: str | None,
        dataset_context: DatasetContext | dict[str, Any] | None = None,
        guideline_context: Mapping[str, Any] | None = None,
        model_id: str | None = None,
    ) -> PlanningResult:
        normalized_source_id = str(source_id or "").strip()
        if not normalized_source_id:
            return PlanningResult(route="general_question")

        context = self._ensure_dataset_context(
            source_id=normalized_source_id,
            dataset_context=dataset_context,
        )
        if not context.available:
            raise FileNotFoundError(f"dataset context unavailable: {normalized_source_id}")

        if should_preflight_explicit_column_issue(user_input):
            explicit_column_issue = find_explicit_column_issue(
                user_input,
                context.columns,
            )
            if explicit_column_issue is not None:
                return PlanningResult(
                    route="analysis",
                    needs_clarification=True,
                    clarification_question=explicit_column_issue.clarification_message(),
                    ask_analysis=True,
                    preprocess_required=False,
                    need_visualization=_contains_any(
                        user_input,
                        _VISUALIZATION_INTENT_TERMS,
                    ),
                    need_report=_contains_any(user_input, _REPORT_INTENT_TERMS),
                    guideline_context_used=bool(
                        (guideline_context or {}).get("has_evidence", False)
                    ),
                )

        deterministic_result = self._try_plan_explicit_outlier(
            user_input=user_input,
            dataset_context=context,
            guideline_context=guideline_context,
        )
        if deterministic_result is not None:
            return deterministic_result

        deterministic_result = self._try_plan_quality_report(
            user_input=user_input,
            dataset_context=context,
            guideline_context=guideline_context,
        )
        if deterministic_result is not None:
            return deterministic_result

        deterministic_result = self._try_plan_product_count(
            user_input=user_input,
            dataset_context=context,
            guideline_context=guideline_context,
        )
        if deterministic_result is not None:
            return deterministic_result

        deterministic_result = self._try_plan_defect_impact_comparison(
            user_input=user_input,
            dataset_context=context,
            guideline_context=guideline_context,
        )
        if deterministic_result is not None:
            return deterministic_result

        decision = self._build_decision(
            user_input=user_input,
            request_context=request_context,
            source_id=normalized_source_id,
            dataset_context=context,
            guideline_context=guideline_context,
            model_id=model_id,
        )
        decision = _apply_planner_decision_guards(decision, user_input)
        if not bool((guideline_context or {}).get("has_evidence", False)):
            decision.guideline_context_used = False
        route = self._resolve_route(decision)
        if route != "analysis":
            return PlanningResult(
                route=route,
                ask_analysis=decision.ask_analysis,
                preprocess_required=decision.preprocess_required,
                need_visualization=decision.need_visualization,
                need_report=decision.need_report,
                guideline_context_used=decision.guideline_context_used,
            )
        if decision.preprocess_required and not _decision_requires_analysis_plan(decision):
            return PlanningResult(
                route="analysis",
                ask_analysis=False,
                preprocess_required=True,
                need_visualization=False,
                need_report=False,
                guideline_context_used=decision.guideline_context_used,
            )

        explicit_column_issue = find_explicit_column_issue(user_input, context.columns)
        if explicit_column_issue is not None:
            return PlanningResult(
                route="analysis",
                needs_clarification=True,
                clarification_question=explicit_column_issue.clarification_message(),
                ask_analysis=decision.ask_analysis,
                preprocess_required=decision.preprocess_required,
                need_visualization=decision.need_visualization,
                need_report=decision.need_report,
                guideline_context_used=decision.guideline_context_used,
            )

        metadata = self._build_metadata_snapshot(context)
        understanding = self._build_question_understanding(
            user_input=user_input,
            dataset_meta=metadata,
            guideline_context=guideline_context,
            model_id=model_id,
        )
        understanding = _repair_time_bucket_defect_understanding(
            understanding=understanding,
            user_input=user_input,
            dataset_context=context,
            dataset_meta=metadata,
        )
        if understanding.ambiguity_status != "clear":
            return PlanningResult(
                route="analysis",
                needs_clarification=True,
                clarification_question=understanding.clarification_message,
                ask_analysis=decision.ask_analysis,
                preprocess_required=decision.preprocess_required,
                need_visualization=decision.need_visualization,
                need_report=decision.need_report,
                guideline_context_used=decision.guideline_context_used,
            )

        column_grounding = self.analysis_processor.ground_columns(
            question_understanding=understanding,
            dataset_meta=metadata,
            raw_question=user_input,
        )
        plan_draft = self._build_analysis_plan_draft(
            user_input=user_input,
            question_understanding=understanding,
            column_grounding=column_grounding,
            dataset_meta=metadata,
            guideline_context=guideline_context,
            model_id=model_id,
        )
        plan_draft = _repair_time_bucket_defect_plan_draft(
            plan_draft=plan_draft,
            user_input=user_input,
            dataset_context=context,
            dataset_meta=metadata,
        )
        if plan_draft.ambiguity_status != "clear":
            clarification_question = (
                plan_draft.clarification_message or understanding.clarification_message
            )
            return PlanningResult(
                route="analysis",
                needs_clarification=True,
                clarification_question=clarification_question,
                ask_analysis=decision.ask_analysis,
                preprocess_required=decision.preprocess_required,
                need_visualization=decision.need_visualization,
                need_report=decision.need_report,
                guideline_context_used=decision.guideline_context_used,
            )

        analysis_plan = self.analysis_processor.validate_and_finalize_plan(
            plan_draft=plan_draft,
            dataset_meta=metadata,
            column_grounding=column_grounding,
        )
        return PlanningResult(
            route="analysis",
            ask_analysis=decision.ask_analysis,
            preprocess_required=decision.preprocess_required,
            analysis_plan=analysis_plan,
            need_visualization=decision.need_visualization,
            need_report=decision.need_report,
            guideline_context_used=decision.guideline_context_used,
        )

    def _build_decision(
        self,
        *,
        user_input: str,
        request_context: str | None,
        source_id: str,
        dataset_context: DatasetContext,
        guideline_context: Mapping[str, Any] | None,
        model_id: str | None,
    ) -> PlannerDecision:
        return self.llm.invoke_structured(
            schema=PlannerDecision,
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("decision.system")),
                HumanMessage(
                    content=(
                        f"user_input:\n{user_input.strip()}\n\n"
                        f"request_context:\n{str(request_context or '').strip()}\n\n"
                        f"source_id:\n{source_id}\n\n"
                        f"dataset_context:\n{self._to_json(trim_fast_path_bulk_context_fields(dataset_context.model_dump()))}\n\n"
                        f"guideline_context:\n{self._to_json(dict(guideline_context or {}))}"
                    )
                ),
            ],
        )

    def _build_question_understanding(
        self,
        *,
        user_input: str,
        dataset_meta: MetadataSnapshot,
        guideline_context: Mapping[str, Any] | None,
        model_id: str | None,
    ) -> QuestionUnderstanding:
        return self.llm.invoke_structured(
            schema=QuestionUnderstanding,
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("question_understanding.system")),
                HumanMessage(
                    content=(
                        f"question:\n{user_input.strip()}\n\n"
                        f"dataset_meta:\n{self._to_json(dataset_meta.model_dump())}\n\n"
                        f"guideline_context:\n{self._to_json(dict(guideline_context or {}))}"
                    )
                ),
            ],
        )

    def _build_analysis_plan_draft(
        self,
        *,
        user_input: str,
        question_understanding: QuestionUnderstanding,
        column_grounding: BaseModel,
        dataset_meta: MetadataSnapshot,
        guideline_context: Mapping[str, Any] | None,
        model_id: str | None,
    ) -> AnalysisPlanDraft:
        return self.llm.invoke_structured(
            schema=AnalysisPlanDraft,
            model_id=model_id,
            messages=[
                SystemMessage(content=PROMPTS.load_prompt("plan_draft.system")),
                HumanMessage(
                    content=(
                        f"question:\n{user_input.strip()}\n\n"
                        f"question_understanding:\n{self._to_json(question_understanding.model_dump())}\n\n"
                        f"column_grounding:\n{self._to_json(column_grounding.model_dump())}\n\n"
                        f"dataset_meta:\n{self._to_json(dataset_meta.model_dump())}\n\n"
                        f"guideline_context:\n{self._to_json(dict(guideline_context or {}))}"
                    )
                ),
            ],
        )

    def _try_plan_quality_report(
        self,
        *,
        user_input: str,
        dataset_context: DatasetContext,
        guideline_context: Mapping[str, Any] | None,
    ) -> PlanningResult | None:
        if not _is_quality_summary_request(user_input):
            return None
        columns = dataset_context.columns
        pass_column = "PassOrFail" if "PassOrFail" in columns else None
        product_columns = [
            *_columns_for_logical_axis(columns, "PART_NO"),
            *_columns_for_logical_axis(columns, "PART_NAME"),
        ]
        reason_columns = _columns_for_logical_axis(columns, "Reason")
        required_columns = _unique_columns([pass_column, *product_columns, *reason_columns])
        if not required_columns:
            return None

        metadata = self._build_metadata_snapshot(dataset_context)
        analysis_plan = AnalysisPlan(
            analysis_type="quality_status_summary",
            objective=(
                "전체 품질 현황, 양품/불량 비율, 불량 사유, 제품별 생산량을 "
                "결정적 집계로 요약합니다."
            ),
            required_columns=required_columns,
            used_columns=required_columns,
            filters=[],
            group_by=[],
            metrics=[
                MetricSpec(
                    name="total_count",
                    aggregation="count",
                    column=None,
                    alias="total_count",
                )
            ],
            derived_columns=[],
            sort_by=[],
            time_context=None,
            expected_output=ExpectedOutputSpec(
                require_summary=True,
                require_table=True,
                require_raw_metrics=True,
                expected_table_columns=["section", "label", "count", "rate"],
                allow_empty_table=False,
                minimum_rows=1,
            ),
            visualization_hint=VisualizationHint(preferred_chart="none"),
            empty_result_policy="success_with_empty_summary",
            metadata_snapshot=metadata,
            codegen_strategy="llm_codegen",
        )
        return PlanningResult(
            route="analysis",
            ask_analysis=True,
            preprocess_required=False,
            analysis_plan=analysis_plan,
            need_visualization=_contains_any(user_input, _VISUALIZATION_INTENT_TERMS),
            need_report=_contains_any(user_input, _REPORT_INTENT_TERMS),
            guideline_context_used=bool((guideline_context or {}).get("has_evidence", False)),
        )

    def _try_plan_product_count(
        self,
        *,
        user_input: str,
        dataset_context: DatasetContext,
        guideline_context: Mapping[str, Any] | None,
    ) -> PlanningResult | None:
        if not _contains_any(user_input, _PRODUCT_COUNT_INTENT_TERMS):
            return None
        target_axis = _select_product_axis(user_input, dataset_context.columns)
        if target_axis is None:
            return None
        required_columns = _columns_for_logical_axis(dataset_context.columns, target_axis)
        if not required_columns:
            return None

        metadata = self._build_metadata_snapshot(dataset_context)
        analysis_plan = AnalysisPlan(
            analysis_type="product_production_count",
            objective=f"{target_axis}별 생산량을 결정적 집계로 계산합니다.",
            required_columns=required_columns,
            used_columns=required_columns,
            filters=[],
            group_by=[target_axis],
            metrics=[
                MetricSpec(
                    name="production_count",
                    aggregation="count",
                    column=None,
                    alias="production_count",
                )
            ],
            derived_columns=[],
            sort_by=[],
            time_context=None,
            expected_output=ExpectedOutputSpec(
                require_summary=True,
                require_table=True,
                require_raw_metrics=True,
                expected_table_columns=[target_axis, "production_count"],
                allow_empty_table=False,
                minimum_rows=1,
                require_group_axis=True,
            ),
            visualization_hint=VisualizationHint(
                preferred_chart="bar",
                x=target_axis,
                y="production_count",
            ),
            empty_result_policy="success_with_empty_summary",
            metadata_snapshot=metadata,
            codegen_strategy="llm_codegen",
        )
        return PlanningResult(
            route="analysis",
            ask_analysis=True,
            preprocess_required=False,
            analysis_plan=analysis_plan,
            need_visualization=_contains_any(user_input, _VISUALIZATION_INTENT_TERMS),
            need_report=_contains_any(user_input, _REPORT_INTENT_TERMS),
            guideline_context_used=bool((guideline_context or {}).get("has_evidence", False)),
        )

    def _try_plan_defect_impact_comparison(
        self,
        *,
        user_input: str,
        dataset_context: DatasetContext,
        guideline_context: Mapping[str, Any] | None,
    ) -> PlanningResult | None:
        if not _is_defect_impact_comparison_request(user_input):
            return None
        metadata = self._build_metadata_snapshot(dataset_context)
        defect_column = _resolve_defect_indicator_column(metadata)
        if defect_column is None:
            return None

        group_by = _select_defect_impact_group_columns(
            user_input=user_input,
            columns=dataset_context.columns,
            defect_column=defect_column,
        )
        metric_columns = _select_defect_impact_numeric_columns(
            user_input=user_input,
            dataset_context=dataset_context,
            defect_column=defect_column,
        )
        if not group_by:
            return None

        metrics = [
            MetricSpec(
                name="defect_rate_by_group",
                aggregation="rate",
                column=defect_column,
                positive_value=1,
                alias="defect_rate_by_group",
            )
        ]
        metrics.extend(
            MetricSpec(
                name=f"avg_{column}",
                aggregation="avg",
                column=column,
                alias=f"avg_{column}",
            )
            for column in metric_columns
        )
        required_columns = _unique_columns(
            [defect_column, *group_by, *metric_columns]
        )
        table_columns = _unique_columns(
            [*group_by, *(metric.alias for metric in metrics)]
        )
        wants_visualization = _contains_any(user_input, _VISUALIZATION_INTENT_TERMS)
        analysis_plan = AnalysisPlan(
            analysis_type="defect_impact_comparison",
            objective=(
                f"{defect_column}=1을 불량으로 보고 요청된 그룹 축별 불량률과 "
                "수치 지표 평균을 결정적으로 비교합니다."
            ),
            required_columns=required_columns,
            used_columns=required_columns,
            filters=[],
            group_by=group_by,
            metrics=metrics,
            derived_columns=[],
            sort_by=[],
            time_context=None,
            expected_output=ExpectedOutputSpec(
                require_summary=True,
                require_table=True,
                require_raw_metrics=True,
                expected_table_columns=table_columns,
                allow_empty_table=False,
                minimum_rows=1,
                require_group_axis=True,
            ),
            visualization_hint=_build_defect_impact_visualization_hint(
                group_by=group_by,
                defect_column=defect_column,
                wants_visualization=wants_visualization,
            ),
            empty_result_policy="success_with_empty_summary",
            metadata_snapshot=metadata,
            codegen_strategy="llm_codegen",
        )
        return PlanningResult(
            route="analysis",
            ask_analysis=True,
            preprocess_required=False,
            analysis_plan=analysis_plan,
            need_visualization=wants_visualization,
            need_report=_contains_any(user_input, _REPORT_INTENT_TERMS),
            guideline_context_used=bool((guideline_context or {}).get("has_evidence", False)),
        )

    def _ensure_dataset_context(
        self,
        *,
        source_id: str,
        dataset_context: DatasetContext | dict[str, Any] | None,
    ) -> DatasetContext:
        if isinstance(dataset_context, DatasetContext):
            return dataset_context
        if isinstance(dataset_context, dict):
            return DatasetContext.model_validate(dataset_context)
        return self.dataset_context_service.build_context(source_id)

    def _try_plan_explicit_outlier(
        self,
        *,
        user_input: str,
        dataset_context: DatasetContext,
        guideline_context: Mapping[str, Any] | None,
    ) -> PlanningResult | None:
        if not _contains_any(user_input, _OUTLIER_INTENT_TERMS):
            return None
        target_column = _find_explicit_column(user_input, dataset_context.columns)
        if target_column is None:
            return None

        metadata = self._build_metadata_snapshot(dataset_context)
        group_by = _select_outlier_context_columns(
            dataset_context=dataset_context,
            target_column=target_column,
        )
        time_column = (
            dataset_context.datetime_columns[0]
            if dataset_context.datetime_columns
            else None
        )
        metrics = [
            MetricSpec(
                name="outlier_target_avg",
                aggregation="avg",
                column=target_column,
                alias=f"{target_column}_avg",
            ),
            MetricSpec(
                name="outlier_target_min",
                aggregation="min",
                column=target_column,
                alias=f"{target_column}_min",
            ),
            MetricSpec(
                name="outlier_target_max",
                aggregation="max",
                column=target_column,
                alias=f"{target_column}_max",
            ),
        ]
        if "PassOrFail" in dataset_context.columns and target_column != "PassOrFail":
            metrics.append(
                MetricSpec(
                    name="defect_rate",
                    aggregation="rate",
                    column="PassOrFail",
                    positive_value=1,
                    alias="defect_rate",
                )
            )

        used_columns = _unique_columns(
            [
                target_column,
                *group_by,
                time_column,
                *(metric.column for metric in metrics),
            ]
        )
        table_columns = _unique_columns(
            [
                *group_by,
                time_column,
                target_column,
                *(metric.alias for metric in metrics),
                "outlier_reason",
            ]
        )
        wants_visualization = _contains_any(user_input, _VISUALIZATION_INTENT_TERMS)
        objective = f"{target_column} 컬럼의 이상치를 탐지하고 관련 원인 후보를 추정합니다."
        if _contains_any(user_input, _ROOT_CAUSE_INTENT_TERMS):
            objective += " 주변 범주형 컬럼별 이상치 집중도를 함께 비교합니다."

        analysis_plan = AnalysisPlan(
            analysis_type="outlier_detection_and_root_cause_inference",
            objective=objective,
            required_columns=used_columns,
            used_columns=used_columns,
            filters=[],
            group_by=group_by,
            metrics=metrics,
            derived_columns=[],
            sort_by=[],
            time_context=TimeContext(
                time_column=time_column,
                range_type="none",
                grain=None,
            )
            if time_column
            else None,
            expected_output=ExpectedOutputSpec(
                require_summary=True,
                require_table=True,
                require_raw_metrics=True,
                expected_table_columns=table_columns,
                allow_empty_table=True,
                minimum_rows=0,
                require_group_axis=bool(group_by),
                require_time_axis=False,
                require_outlier_info=True,
            ),
            visualization_hint=VisualizationHint(
                preferred_chart="bar" if wants_visualization else "none",
                x=group_by[0] if wants_visualization and group_by else None,
                y="defect_rate"
                if any(metric.alias == "defect_rate" for metric in metrics)
                else metrics[0].alias,
                series=None,
                caption="이상치 원인 후보 비교" if group_by else None,
            ),
            empty_result_policy="success_with_empty_summary",
            metadata_snapshot=metadata,
            codegen_strategy="llm_codegen",
        )
        return PlanningResult(
            route="analysis",
            ask_analysis=True,
            preprocess_required=False,
            analysis_plan=analysis_plan,
            need_visualization=wants_visualization,
            need_report=_contains_any(user_input, _REPORT_INTENT_TERMS),
            guideline_context_used=bool((guideline_context or {}).get("has_evidence", False)),
        )

    @staticmethod
    def _resolve_route(decision: PlannerDecision) -> PlanningRoute:
        if decision.is_general_question:
            return "general_question"
        if (
            decision.ask_analysis
            or decision.preprocess_required
            or decision.need_visualization
            or decision.need_report
        ):
            return "analysis"
        return "fallback_rag"

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

    @staticmethod
    def _to_json(payload: Mapping[str, Any]) -> str:
        return json.dumps(dict(payload), ensure_ascii=False, default=str)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = str(text or "").lower()
    return any(term.lower() in normalized for term in terms)


def _is_quality_summary_request(user_input: str) -> bool:
    text = str(user_input or "").lower()
    if "전체 품질 현황" in text or "품질 현황" in text:
        return True
    if _contains_any(user_input, _REPORT_INTENT_TERMS) and _contains_any(
        user_input,
        _QUALITY_SUMMARY_INTENT_TERMS,
    ):
        return True
    return "양품" in text and (
        "불량 비율" in text
        or "불량 사유" in text
        or "제품별 생산량" in text
    )


def _select_product_axis(user_input: str, columns: list[str]) -> str | None:
    text = str(user_input or "").lower()
    if "part_name" in text or "제품명" in text:
        for axis in ("PART_NAME", "PART_NO"):
            if _columns_for_logical_axis(columns, axis):
                return axis
        return None
    if "part_no" in text or "제품" in text or "생산량" in text:
        for axis in ("PART_NO", "PART_NAME"):
            if _columns_for_logical_axis(columns, axis):
                return axis
    return None


def _is_defect_impact_comparison_request(user_input: str) -> bool:
    text = str(user_input or "").lower()
    defect_terms = ("불량", "defect", "failure", "fail")
    comparison_terms = (
        "영향",
        "비교",
        "차이",
        "관계",
        "impact",
        "compare",
        "effect",
        "influence",
    )
    return (
        any(term in text for term in defect_terms)
        and any(term in text for term in comparison_terms)
    )


def _select_defect_impact_group_columns(
    *,
    user_input: str,
    columns: list[str],
    defect_column: str,
) -> list[str]:
    selected: list[str] = []
    if _pass_fail_split_requested(user_input, defect_column):
        selected.append(defect_column)

    for axis in ("EQUIP_CD", "EQUIP_NAME", "PART_NO", "PART_NAME", "Reason"):
        if _logical_axis_requested(user_input, axis):
            selected.extend(_columns_for_logical_axis(columns, axis))
    return _unique_columns([column for column in selected if column in columns])


def _pass_fail_split_requested(user_input: str, defect_column: str) -> bool:
    text = str(user_input or "").lower()
    loose_text = _normalize_loose_identifier(user_input)
    loose_defect_column = _normalize_loose_identifier(defect_column)
    split_terms = ("양품", "정상", "pass/fail", "pass fail")
    return (
        loose_defect_column in loose_text
        or any(term in text for term in split_terms)
    )


def _select_defect_impact_numeric_columns(
    *,
    user_input: str,
    dataset_context: DatasetContext,
    defect_column: str,
) -> list[str]:
    selected: list[str] = []
    loose_text = _normalize_loose_identifier(user_input)
    for column in dataset_context.numeric_columns:
        if column == defect_column:
            continue
        loose_column = _normalize_loose_identifier(column)
        if loose_column and loose_column in loose_text:
            selected.append(column)
    return _unique_columns(selected)


def _build_defect_impact_visualization_hint(
    *,
    group_by: list[str],
    defect_column: str,
    wants_visualization: bool,
) -> VisualizationHint:
    if not wants_visualization:
        return VisualizationHint(preferred_chart="none")

    non_defect_axes = [column for column in group_by if column != defect_column]
    x_axis = (
        non_defect_axes[0]
        if non_defect_axes
        else (group_by[0] if group_by else None)
    )
    series_axis = None
    if defect_column in group_by and x_axis != defect_column:
        series_axis = defect_column
    elif len(non_defect_axes) > 1:
        series_axis = non_defect_axes[1]

    return VisualizationHint(
        preferred_chart="bar",
        x=x_axis,
        y="defect_rate_by_group",
        series=series_axis,
    )


def _logical_axis_requested(user_input: str, logical_axis: str) -> bool:
    text = str(user_input or "").lower()
    loose_text = _normalize_loose_identifier(user_input)
    terms_by_axis = {
        "EQUIP_CD": ("equipcd", "equipment", "설비", "장비"),
        "EQUIP_NAME": ("equipname", "equipment", "설비명", "설비", "장비"),
        "PART_NO": ("partno", "part", "제품", "품번"),
        "PART_NAME": ("partname", "product", "제품명", "제품"),
        "Reason": ("reason", "원인", "사유"),
    }
    terms = terms_by_axis.get(logical_axis, ())
    return any(term in text or term in loose_text for term in terms)


def _columns_for_logical_axis(columns: list[str], logical_axis: str) -> list[str]:
    if logical_axis in columns:
        return [logical_axis]
    prefix = f"{logical_axis}_"
    return [column for column in columns if column.startswith(prefix)]


def _find_explicit_column(user_input: str, columns: list[str]) -> str | None:
    by_exact = {column: column for column in columns}
    by_lower = {column.lower(): column for column in columns}
    by_loose = {_normalize_loose_identifier(column): column for column in columns}

    for match in _EXACT_COLUMN_RE.finditer(str(user_input or "")):
        term = match.group(1).strip()
        if not term:
            continue
        if term in by_exact:
            return by_exact[term]
        lower_term = term.lower()
        if lower_term in by_lower:
            return by_lower[lower_term]
        loose_term = _normalize_loose_identifier(term)
        if loose_term in by_loose:
            return by_loose[loose_term]

    loose_question = _normalize_loose_identifier(user_input)
    for column in sorted(columns, key=len, reverse=True):
        loose_column = _normalize_loose_identifier(column)
        if loose_column and loose_column in loose_question:
            return column
    return None


def _select_outlier_context_columns(
    *,
    dataset_context: DatasetContext,
    target_column: str,
) -> list[str]:
    preferred_columns = (
        "EQUIP_CD",
        "EQUIP_NAME",
        "PART_NAME",
        "PART_NO",
        "Reason",
        "PassOrFail",
    )
    candidates = [
        *preferred_columns,
        *dataset_context.group_key_columns,
        *dataset_context.categorical_columns,
    ]
    selected: list[str] = []
    available = set(dataset_context.columns)
    for column in candidates:
        if column == target_column or column not in available or column in selected:
            continue
        if column not in preferred_columns and (
            _looks_like_row_identifier(column)
            or _looks_like_encoded_indicator_column(column)
        ):
            continue
        selected.append(column)
        if len(selected) >= 4:
            break
    return selected


def _looks_like_row_identifier(column: str) -> bool:
    normalized = _normalize_loose_identifier(column)
    return normalized in {"id", "index", "unnamed0"} or normalized.endswith("id")


def _looks_like_encoded_indicator_column(column: str) -> bool:
    return (
        len(column) > 48
        or bool(re.search(r"\d{4}[-_]\d{1,2}", column))
        or bool(re.search(r"_[A-Z0-9_-]*\d[A-Z0-9_-]*$", column))
        or ":" in column
        or "오전" in column
        or "오후" in column
        or any(
            column.startswith(f"{base}_")
            for base in ("PART_NO", "PART_NAME", "EQUIP_CD", "EQUIP_NAME", "Reason")
        )
    )


def _unique_columns(values: Sequence[str | None]) -> list[str]:
    columns: list[str] = []
    for value in values:
        column = str(value or "").strip()
        if column and column not in columns:
            columns.append(column)
    return columns


def _normalize_loose_identifier(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "", str(value or "").lower())


def _should_force_skip_preprocess_for_analysis_request(user_input: str) -> bool:
    text = user_input.lower()
    analysis_terms = (
        "비율",
        "건수",
        "생산량",
        "그래프",
        "시각화",
        "차트",
        "count",
        "ratio",
    )
    preprocess_terms = (
        "전처리",
        "결측",
        "결측치",
        "정규화",
        "표준화",
        "스케일",
        "scale",
        "normalize",
        "standardize",
        "인코딩",
        "형변환",
        "파생",
        "컬럼명",
        "제거한 뒤",
        "채운 뒤",
    )
    return any(term in text for term in analysis_terms) and not any(
        term in text for term in preprocess_terms
    )


def _user_requested_visualization(user_input: str) -> bool:
    text = user_input.lower()
    visualization_terms = (
        "그래프",
        "시각화",
        "차트",
        "plot",
        "chart",
        "graph",
        "visualize",
        "visualization",
    )
    return any(term in text for term in visualization_terms)


def _decision_requires_analysis_plan(decision: PlannerDecision) -> bool:
    return bool(
        decision.ask_analysis
        or decision.need_visualization
        or decision.need_report
    )


def _repair_time_bucket_defect_understanding(
    *,
    understanding: QuestionUnderstanding,
    user_input: str,
    dataset_context: DatasetContext,
    dataset_meta: MetadataSnapshot,
) -> QuestionUnderstanding:
    defect_column = _resolve_defect_indicator_column(dataset_meta)
    time_column = _resolve_time_bucket_column(dataset_meta)
    if not (
        defect_column
        and time_column
        and _is_time_bucket_defect_request(user_input)
        and _dataset_supports_binary_indicator(dataset_context, defect_column)
    ):
        return understanding

    return understanding.model_copy(
        update={
            "analysis_goal": _append_unique(
                understanding.analysis_goal,
                [
                    "날짜별 불량 건수 집계",
                    f"{defect_column}=1을 불량 indicator로 사용",
                ],
            ),
            "metric_keywords": _append_unique(
                understanding.metric_keywords,
                [defect_column, "defect_count", "defect_rate"],
            ),
            "group_keywords": _append_unique(
                understanding.group_keywords,
                [time_column, "date", "일별"],
            ),
            "filter_conditions": _append_unique_filters(
                understanding.filter_conditions,
                [FilterCondition(column=defect_column, operator="eq", value=1)],
            ),
            "time_context": understanding.time_context
            or TimeContext(time_column=time_column, range_type="none", grain="day"),
            "ambiguity_status": "clear",
            "clarification_message": "",
        }
    )


def _repair_time_bucket_defect_plan_draft(
    *,
    plan_draft: AnalysisPlanDraft,
    user_input: str,
    dataset_context: DatasetContext,
    dataset_meta: MetadataSnapshot,
) -> AnalysisPlanDraft:
    if plan_draft.ambiguity_status == "clear":
        return plan_draft
    defect_column = _resolve_defect_indicator_column(dataset_meta)
    time_column = _resolve_time_bucket_column(dataset_meta)
    if not (
        defect_column
        and time_column
        and _is_time_bucket_defect_request(user_input)
        and _dataset_supports_binary_indicator(dataset_context, defect_column)
    ):
        return plan_draft

    return AnalysisPlanDraft(
        analysis_type="daily_defect_analysis",
        objective=(
            f"{time_column}를 day 단위로 버킷팅해 날짜별 불량 건수와 "
            f"전체 건수, 불량률을 계산합니다. {defect_column}=1은 불량입니다."
        ),
        group_by=[],
        metrics=[
            MetricSpec(
                name="defect_count",
                aggregation="sum",
                column=defect_column,
                positive_value=1,
                alias="defect_count",
            ),
            MetricSpec(
                name="total_count",
                aggregation="count",
                column=None,
                alias="total_count",
            ),
            MetricSpec(
                name="defect_rate",
                aggregation="rate",
                column=defect_column,
                positive_value=1,
                alias="defect_rate",
            ),
        ],
        sort_by=[SortSpec(column=time_column, direction="asc")],
        time_context=TimeContext(
            time_column=time_column,
            range_type="none",
            grain="day",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        ambiguity_status="clear",
    )


def _is_time_bucket_defect_request(user_input: str) -> bool:
    text = user_input.lower()
    defect_terms = ("불량", "defect", "failure", "fail")
    time_terms = (
        "날짜별",
        "일별",
        "월별",
        "주별",
        "시간별",
        "date",
        "daily",
        "weekly",
        "monthly",
        "time",
    )
    metric_terms = ("건수", "count", "개수", "횟수", "비율", "률", "rate")
    return (
        any(term in text for term in defect_terms)
        and any(term in text for term in time_terms)
        and any(term in text for term in metric_terms)
    )


def _resolve_defect_indicator_column(dataset_meta: MetadataSnapshot) -> str | None:
    for column in dataset_meta.columns:
        if column.lower() == "passorfail":
            return column
    return None


def _resolve_time_bucket_column(dataset_meta: MetadataSnapshot) -> str | None:
    if dataset_meta.datetime_columns:
        return dataset_meta.datetime_columns[0]
    preferred = ("timestamp", "time_stamp", "date", "datetime")
    for expected in preferred:
        for column in dataset_meta.columns:
            if column.lower() == expected:
                return column
    for column in dataset_meta.columns:
        normalized = column.lower()
        if "timestamp" in normalized or "date" in normalized:
            return column
    return None


def _dataset_supports_binary_indicator(
    dataset_context: DatasetContext,
    column: str,
) -> bool:
    samples = list(dataset_context.column_value_samples.get(column, []))
    samples.extend(
        row.get(column) for row in dataset_context.sample_rows if column in row
    )
    normalized = {
        str(value).strip().lower()
        for value in samples
        if value is not None and str(value).strip() != ""
    }
    if not normalized:
        return True
    return normalized <= {"0", "0.0", "1", "1.0", "true", "false"}


def _append_unique(existing: list[str], additions: list[str]) -> list[str]:
    values = list(existing)
    seen = set(values)
    for value in additions:
        if value not in seen:
            values.append(value)
            seen.add(value)
    return values


def _append_unique_filters(
    existing: list[FilterCondition],
    additions: list[FilterCondition],
) -> list[FilterCondition]:
    values = list(existing)
    seen = {(item.column, item.operator, str(item.value)) for item in values}
    for item in additions:
        key = (item.column, item.operator, str(item.value))
        if key not in seen:
            values.append(item)
            seen.add(key)
    return values


def _apply_planner_decision_guards(
    decision: PlannerDecision,
    user_input: str,
) -> PlannerDecision:
    if _should_force_skip_preprocess_for_analysis_request(user_input):
        decision.preprocess_required = False
    if decision.need_visualization and not _user_requested_visualization(user_input):
        decision.need_visualization = False
    return decision


def build_handoff_from_planning_result(planning_result: PlanningResult) -> dict[str, Any]:
    route = planning_result.route
    if route == "general_question":
        next_step = "general_question"
    elif route == "analysis":
        next_step = "analysis"
    else:
        next_step = "fallback_rag"

    return {
        "next_step": next_step,
        "ask_analysis": bool(
            planning_result.ask_analysis or planning_result.analysis_plan is not None
        ),
        "ask_preprocess": planning_result.preprocess_required,
        "ask_visualization": planning_result.need_visualization,
        "ask_report": planning_result.need_report,
        "ask_guideline": planning_result.guideline_context_used,
    }


def build_preprocess_decision_from_planning_result(
    planning_result: PlanningResult,
) -> dict[str, Any]:
    if planning_result.preprocess_required:
        return {
            "step": "run_preprocess",
            "reason_summary": "planner가 전처리가 필요하다고 판단했습니다.",
        }
    return {
        "step": "skip_preprocess",
        "reason_summary": "planner가 전처리 없이 진행 가능하다고 판단했습니다.",
    }
