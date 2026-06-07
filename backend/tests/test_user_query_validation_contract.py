from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from backend.app.core.ai import LLMGateway
from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisPlanDraft,
    MetricSpec,
    QuestionUnderstanding,
    VisualizationHint,
)
from backend.app.modules.planner.schemas import PlannerDecision
from backend.app.modules.planner.query_validation import find_explicit_column_issue
from backend.app.modules.planner.service import PlannerService
from backend.app.modules.profiling.schemas import DatasetContext


class _StaticMoldDatasetContextService:
    def build_context(
        self,
        source_id: str,
        *,
        include_ai_aliases: bool | None = None,
    ) -> DatasetContext:
        return _mold_dataset_context().model_copy(update={"source_id": source_id})


class _DecisionOnlyLLM(LLMGateway):
    def __init__(self, decision: PlannerDecision) -> None:
        super().__init__(default_model="test-model")
        self._decision = decision

    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> BaseModel:
        _ = (messages, model_id, temperature)
        if schema is PlannerDecision:
            return self._decision
        raise AssertionError(f"unexpected schema: {schema}")


class _PreprocessAnalysisLLM(LLMGateway):
    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> BaseModel:
        _ = (messages, model_id, temperature)
        if schema is PlannerDecision:
            return PlannerDecision(
                ask_analysis=True,
                preprocess_required=True,
            )
        if schema is QuestionUnderstanding:
            return QuestionUnderstanding(
                analysis_goal=["Analyze quality after numeric preprocessing"],
                metric_keywords=["count"],
                group_keywords=["PassOrFail"],
                ambiguity_status="clear",
            )
        if schema is AnalysisPlanDraft:
            return AnalysisPlanDraft(
                analysis_type="quality_count",
                objective="불량 여부별 건수를 계산합니다.",
                group_by=["PassOrFail"],
                metrics=[
                    MetricSpec(
                        name="row_count",
                        aggregation="count",
                        alias="row_count",
                    )
                ],
                visualization_hint=VisualizationHint(preferred_chart="none"),
            )
        raise AssertionError(f"unexpected schema: {schema}")


def test_preprocess_analysis_phrase_does_not_treat_generic_column_type_as_missing() -> None:
    service = _planner_service(_PreprocessAnalysisLLM(default_model="test-model"))

    result = service.plan(
        user_input="수치형 컬럼을 표준화한 뒤 불량 여부와의 관계를 분석해줘.",
        request_context=None,
        source_id="moldset-source",
        dataset_context=_mold_dataset_context(),
        guideline_context=None,
        model_id="test-model",
    )

    assert result.needs_clarification is False
    assert result.preprocess_required is True
    assert result.ask_analysis is True
    assert result.analysis_plan is not None


def test_dataset_column_description_stays_on_fallback_rag_route() -> None:
    service = _planner_service(
        _DecisionOnlyLLM(
            PlannerDecision(
                ask_analysis=False,
                preprocess_required=False,
            )
        )
    )

    result = service.plan(
        user_input="Mold_Temperature 컬럼 설명해줘.",
        request_context=None,
        source_id="moldset-source",
        dataset_context=_mold_dataset_context(),
        guideline_context=None,
        model_id="test-model",
    )

    assert result.route == "fallback_rag"
    assert result.needs_clarification is False


def test_preprocess_only_missing_column_reference_stays_on_preprocess_route() -> None:
    service = _planner_service(
        _DecisionOnlyLLM(
            PlannerDecision(
                ask_analysis=False,
                preprocess_required=True,
            )
        )
    )

    result = service.plan(
        user_input="Mold_Temperature 컬럼명을 정리해줘.",
        request_context=None,
        source_id="moldset-source",
        dataset_context=_mold_dataset_context(),
        guideline_context=None,
        model_id="test-model",
    )

    assert result.route == "analysis"
    assert result.needs_clarification is False
    assert result.preprocess_required is True
    assert result.ask_analysis is False


def test_korean_domain_concept_column_phrase_is_not_missing_column() -> None:
    issue = find_explicit_column_issue(
        "제품 컬럼별 불량률을 분석해줘.",
        ["PART_NO", "PART_NAME", "PassOrFail"],
    )

    assert issue is None


def test_english_domain_concept_column_phrase_is_not_missing_column() -> None:
    issue = find_explicit_column_issue(
        "product 컬럼별 불량률을 분석해줘.",
        ["PART_NO", "PART_NAME", "PassOrFail"],
    )

    assert issue is None


def _planner_service(llm: LLMGateway) -> PlannerService:
    service = PlannerService(
        dataset_context_service=_StaticMoldDatasetContextService(),
        analysis_processor=AnalysisProcessor(),
        default_model="test-model",
    )
    service.llm = llm
    return service


def _mold_dataset_context() -> DatasetContext:
    temperature_columns = [f"Mold_Temperature_{number}" for number in range(1, 13)]
    columns = [
        "Max_Injection_Pressure",
        *temperature_columns,
        "PassOrFail",
    ]
    return DatasetContext(
        source_id="moldset-source",
        filename="moldset.csv",
        available=True,
        row_count_total=100,
        row_count_sample=3,
        column_count=len(columns),
        columns=columns,
        dtypes={column: "float64" for column in columns},
        numeric_columns=columns,
        categorical_columns=[],
        sample_rows=[],
    )
