from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisPlanDraft,
    FilterCondition,
    MetricSpec,
    QuestionUnderstanding,
    VisualizationHint,
)
from backend.app.modules.planner.schemas import PlannerDecision, PlanningResult
from backend.app.modules.planner.service import PlannerService
from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.modules.rag.service import RetrievedChunk


GUIDELINE_EVIDENCE_SUMMARY = (
    "제품은 PART_NAME이고 불량은 PassOrFail=1입니다. "
    "불량률은 불량 건수 / 전체 건수로 계산합니다."
)


class ActiveGuidelineService:
    def __init__(
        self,
        *,
        active: SimpleNamespace | None,
        guidelines: dict[str, SimpleNamespace],
    ) -> None:
        self._active = active
        self._guidelines = guidelines

    def get_active_guideline(self) -> SimpleNamespace | None:
        return self._active

    def get_guideline_by_source_id(self, source_id: str) -> SimpleNamespace | None:
        return self._guidelines.get(source_id)


class FakeGuidelineRagService:
    def __init__(self, *, retrieved: list[RetrievedChunk] | None = None) -> None:
        self._retrieved = retrieved or []

    def ensure_index_for_guideline(self, guideline: SimpleNamespace) -> dict[str, str]:
        return {"status": "existing", "source_id": str(guideline.source_id)}

    def query_for_source(
        self,
        *,
        query: str,
        source_id: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        return self._retrieved[:top_k]

    def build_context(self, retrieved: list[RetrievedChunk]) -> str:
        return "\n\n".join(item.content for item in retrieved)


class GuidelineSummaryGateway:
    def __init__(self, *, default_model: str) -> None:
        self.default_model = default_model

    def invoke_structured(
        self,
        *,
        schema: type[Any],
        model_id: str | None,
        messages: list[Any],
    ) -> Any:
        return schema(evidence_summary=GUIDELINE_EVIDENCE_SUMMARY)


class NoopRagService:
    def ensure_index_for_source(self, source_id: str) -> dict[str, str]:
        return {"status": "no_source", "source_id": source_id}

    def query_for_source(self, *, query: str, top_k: int, source_id: str) -> list[Any]:
        return []

    def build_context(self, retrieved: list[Any]) -> str:
        return ""


class PlannerMustNotRun:
    def plan(self, **_: Any) -> PlanningResult:
        raise AssertionError("guideline-only requests must not fall through to planner")


class PlannerMustNotRunWithContext(PlannerMustNotRun):
    def __init__(self) -> None:
        self.dataset_context_service = _StaticContextService()


class GuidelineAwarePlannerLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def invoke_structured(
        self,
        *,
        schema: type[Any],
        model_id: str | None,
        messages: list[Any],
    ) -> Any:
        prompt = "\n\n".join(
            str(getattr(message, "content", "")) for message in messages
        )
        self.prompts.append(prompt)
        if schema is PlannerDecision:
            return PlannerDecision(
                ask_analysis=True,
                need_visualization=True,
                guideline_context_used=True,
            )
        if schema is QuestionUnderstanding:
            return _understanding_for_prompt(prompt)
        if schema is AnalysisPlanDraft:
            return _plan_draft_for_prompt(prompt)
        raise AssertionError(f"unexpected schema: {schema}")


class TraceShapedDefectRatePlannerLLM(GuidelineAwarePlannerLLM):
    def invoke_structured(
        self,
        *,
        schema: type[Any],
        model_id: str | None,
        messages: list[Any],
    ) -> Any:
        prompt = "\n\n".join(
            str(getattr(message, "content", "")) for message in messages
        )
        self.prompts.append(prompt)
        if schema is PlannerDecision:
            return PlannerDecision(
                ask_analysis=True,
                guideline_context_used=True,
            )
        if schema is QuestionUnderstanding:
            return QuestionUnderstanding(
                analysis_goal=[
                    "Compute product-wise defect rate",
                    "Group by product identifiers",
                ],
                metric_keywords=[
                    "defect_rate",
                    "defective_count",
                    "total_count",
                ],
                group_keywords=["PART_NO", "PART_NAME", "EQUIP_NAME"],
                ambiguity_status="clear",
            )
        if schema is AnalysisPlanDraft:
            return AnalysisPlanDraft(
                analysis_type="defect_rate_by_group",
                objective="제품별 불량률을 계산합니다. PassOrFail=1은 불량입니다.",
                group_by=["PART_NO", "PART_NAME", "EQUIP_NAME"],
                metrics=[
                    MetricSpec(
                        name="defect_rate",
                        aggregation="rate",
                        column="PassOrFail",
                        positive_value=1,
                        alias="defect_rate",
                    ),
                    MetricSpec(
                        name="defective_count",
                        aggregation="sum",
                        column="PassOrFail",
                        positive_value=1,
                        alias="defective_count",
                    ),
                    MetricSpec(
                        name="total_count",
                        aggregation="count",
                        alias="total_count",
                    ),
                ],
                visualization_hint=VisualizationHint(preferred_chart="none"),
                ambiguity_status="clear",
            )
        raise AssertionError(f"unexpected schema: {schema}")


def guideline(source_id: str = "guideline-source") -> SimpleNamespace:
    return SimpleNamespace(
        source_id=source_id,
        guideline_id="guide_current",
        filename="manufacturing-guideline.pdf",
    )


def guideline_chunk(source_id: str = "guideline-source") -> RetrievedChunk:
    return RetrievedChunk(
        source_id=source_id,
        chunk_id=0,
        score=0.95,
        content=GUIDELINE_EVIDENCE_SUMMARY,
    )


def dataset_context() -> DatasetContext:
    return DatasetContext(
        source_id="dataset-source",
        filename="quality.csv",
        available=True,
        row_count_total=4,
        row_count_sample=4,
        column_count=4,
        columns=["PART_NO", "PART_NAME", "EQUIP_NAME", "PassOrFail"],
        dtypes={
            "PART_NO": "object",
            "PART_NAME": "object",
            "EQUIP_NAME": "object",
            "PassOrFail": "int64",
        },
        numeric_columns=["PassOrFail"],
        categorical_columns=["PART_NO", "PART_NAME", "EQUIP_NAME"],
        sample_rows=[
            {
                "PART_NO": "P1",
                "PART_NAME": "A",
                "EQUIP_NAME": "E1",
                "PassOrFail": 1,
            },
            {
                "PART_NO": "P1",
                "PART_NAME": "A",
                "EQUIP_NAME": "E1",
                "PassOrFail": 0,
            },
            {
                "PART_NO": "P2",
                "PART_NAME": "B",
                "EQUIP_NAME": "E2",
                "PassOrFail": 1,
            },
            {
                "PART_NO": "P2",
                "PART_NAME": "B",
                "EQUIP_NAME": "E2",
                "PassOrFail": 0,
            },
        ],
    )


def planner_service(llm: GuidelineAwarePlannerLLM) -> PlannerService:
    service = PlannerService(
        dataset_context_service=cast(Any, _ContextService()),
        analysis_processor=AnalysisProcessor(),
        default_model="test-model",
    )
    service.llm = cast(Any, llm)
    return service


def guideline_context_payload() -> dict[str, Any]:
    return {
        "guideline_source_id": "guideline-source",
        "filename": "manufacturing-guideline.pdf",
        "status": "retrieved",
        "retrieved_count": 1,
        "has_evidence": True,
        "evidence_summary": GUIDELINE_EVIDENCE_SUMMARY,
    }


class _ContextService:
    def build_context(self, source_id: str) -> DatasetContext:
        raise AssertionError(f"unexpected dataset context lookup: {source_id}")


class _StaticContextService:
    def build_context(self, source_id: str) -> DatasetContext:
        context = dataset_context()
        return context.model_copy(update={"source_id": source_id})


def _contains_guideline_defect_mapping(prompt: str) -> bool:
    return (
        '"has_evidence": true' in prompt
        and "PART_NAME" in prompt
        and "PassOrFail=1" in prompt
        and "불량 건수 / 전체 건수" in prompt
    )


def _understanding_for_prompt(prompt: str) -> QuestionUnderstanding:
    if not _contains_guideline_defect_mapping(prompt):
        return QuestionUnderstanding(
            ambiguity_status="needs_clarification",
            clarification_message="제품/불량률 매핑을 확인해야 합니다.",
        )
    return QuestionUnderstanding(
        analysis_goal=["제품별 불량률 막대그래프"],
        metric_keywords=["PassOrFail"],
        group_keywords=["PART_NAME"],
        filter_conditions=[FilterCondition(column="PassOrFail", operator="eq", value=1)],
        ambiguity_status="clear",
    )


def _plan_draft_for_prompt(prompt: str) -> AnalysisPlanDraft:
    if not _contains_guideline_defect_mapping(prompt):
        return AnalysisPlanDraft(
            analysis_type="descriptive",
            objective="제품별 불량률 계획을 확정할 수 없습니다.",
            metrics=[
                MetricSpec(
                    name="row_count",
                    aggregation="count",
                    alias="row_count",
                )
            ],
            ambiguity_status="needs_clarification",
            clarification_message="가이드라인 매핑이 필요합니다.",
        )
    return AnalysisPlanDraft(
        analysis_type="descriptive",
        objective="PART_NAME별 PassOrFail=1 비율을 계산해 막대그래프로 표시합니다.",
        group_by=["PART_NAME"],
        metrics=[
            MetricSpec(
                name="defect_rate",
                aggregation="rate",
                column="PassOrFail",
                positive_value=1,
                alias="defect_rate",
            )
        ],
        visualization_hint=VisualizationHint(
            preferred_chart="bar",
            x="PART_NAME",
            y="defect_rate",
        ),
        ambiguity_status="clear",
    )
