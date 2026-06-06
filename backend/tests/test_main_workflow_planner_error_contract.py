from __future__ import annotations

from typing import Any

from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.orchestration.builder import build_main_workflow
from backend.tests.guideline_first_fakes import (
    ActiveGuidelineService,
    FakeGuidelineRagService,
    NoopRagService,
    dataset_context,
)


class _StaticDatasetContextService:
    def build_context(self, source_id: str) -> DatasetContext:
        return dataset_context().model_copy(update={"source_id": source_id})


class _PlanValidationFailurePlanner:
    def __init__(self) -> None:
        self.dataset_context_service = _StaticDatasetContextService()

    def plan(self, **_: Any) -> object:
        raise ValueError("TimeStamp group_by validation failed")


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
