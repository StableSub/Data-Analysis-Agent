from __future__ import annotations

from collections.abc import Sequence

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from backend.app.core.ai import LLMGateway
from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.planner.service import PlannerService
from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.orchestration.builder import build_main_workflow
from backend.tests.guideline_first_fakes import (
    ActiveGuidelineService,
    FakeGuidelineRagService,
    NoopRagService,
    dataset_context,
)


MISSING_COLUMN_QUESTION = (
    "Mold_Temperature 컬럼과 Max_Injection_Pressure 컬럼의 상관관계를 "
    "분석하고 불량과의 관련성을 설명해줘."
)


class _StaticDatasetContextService:
    def build_context(self, source_id: str) -> DatasetContext:
        return dataset_context().model_copy(update={"source_id": source_id})


class _StaticMoldDatasetContextService:
    def build_context(
        self,
        source_id: str,
        *,
        include_ai_aliases: bool | None = None,
    ) -> DatasetContext:
        _ = include_ai_aliases
        return _mold_dataset_context().model_copy(update={"source_id": source_id})


class _PlanValidationFailurePlanner:
    def __init__(self) -> None:
        self.dataset_context_service: _StaticDatasetContextService = (
            _StaticDatasetContextService()
        )

    def plan(self, **_: object) -> object:
        raise ValueError("TimeStamp group_by validation failed")


class _UnexpectedPlannerLLM(LLMGateway):
    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> BaseModel:
        _ = (schema, messages, model_id, temperature)
        raise AssertionError("obvious explicit missing-column analysis should not call LLM")


def test_missing_explicit_column_returns_clarification_not_planning_failure() -> None:
    planner_service = _planner_service()

    result = planner_service.plan(
        user_input=MISSING_COLUMN_QUESTION,
        request_context=None,
        source_id="moldset-source",
        dataset_context=_mold_dataset_context(),
        guideline_context=None,
        model_id="test-model",
    )

    assert result.needs_clarification is True
    assert result.analysis_plan is None
    assert result.ask_analysis is True
    assert "Mold_Temperature" in result.clarification_question
    assert "Mold_Temperature_1" in result.clarification_question
    assert "Max_Injection_Pressure" not in result.clarification_question
    assert "분석 계획을 만들 수 없습니다" not in result.clarification_question


def test_main_workflow_missing_user_column_finishes_as_clarification() -> None:
    workflow = build_main_workflow(
        planner_service=_planner_service(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=NoopRagService(),
        guideline_service=ActiveGuidelineService(active=None, guidelines={}),
        guideline_rag_service=FakeGuidelineRagService(),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": MISSING_COLUMN_QUESTION,
            "source_id": "moldset-source",
            "model_id": "test-model",
        }
    )

    assert result.get("final_status") != "fail"
    assert "workflow_error" not in result
    assert result["output"]["type"] == "clarification"
    assert "Mold_Temperature" in result["output"]["content"]
    assert "Mold_Temperature_1" in result["output"]["content"]
    assert "planning_failed" not in str(result["output"])


def test_main_workflow_planner_exception_surfaces_as_plan_validation_failure() -> None:
    workflow = build_main_workflow(
        planner_service=_PlanValidationFailurePlanner(),
        analysis_service=object(),
        preprocess_service=object(),
        eda_service=object(),
        rag_service=NoopRagService(),
        guideline_service=ActiveGuidelineService(active=None, guidelines={}),
        guideline_rag_service=FakeGuidelineRagService(),
        visualization_service=object(),
        report_service=object(),
        default_model="test-model",
    )

    result = workflow.invoke(
        {
            "user_input": "제품별 불량률을 분석해줘.",
            "source_id": "dataset-source",
            "model_id": "test-model",
        }
    )

    assert result["final_status"] == "fail"
    assert result["workflow_error"]["stage"] == "plan_validation"
    assert result["workflow_error"]["error_code"] == "planning_failed"
    assert result["workflow_error"]["source"] == "main_planner"
    assert result["workflow_error"]["diagnostic_message"] == (
        "TimeStamp group_by validation failed"
    )
    assert result["output"]["type"] == "planning_failed"
    assert "분석 계획을 만들 수 없습니다" in result["output"]["content"]
    assert "기준 컬럼" in result["output"]["content"]
    assert "지표와 기준 컬럼을 지정" in result["output"]["content"]
    assert "TimeStamp group_by validation failed" not in result["output"]["content"]


def _planner_service() -> PlannerService:
    service = PlannerService(
        dataset_context_service=_StaticMoldDatasetContextService(),
        analysis_processor=AnalysisProcessor(),
        default_model="test-model",
    )
    service.llm = _UnexpectedPlannerLLM(default_model="test-model")
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
