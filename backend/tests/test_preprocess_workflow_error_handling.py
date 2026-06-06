from __future__ import annotations

from typing import Any, cast

from pydantic import ValidationError

from backend.app.modules.preprocess.planner import PreprocessPlan
from backend.app.modules.preprocess.executor import execute_preprocess_plan
from backend.app.orchestration.workflows.preprocess import (
    _build_preprocess_plan_failed_output,
    _route_after_preprocess_planner,
)


class _FailingPreprocessService:
    def apply(self, *, source_id: str, operations: list[object]) -> object:
        raise ValueError("Column not found: Clamp_Open_Position")


def _scale_method_validation_error() -> ValidationError:
    try:
        PreprocessPlan.model_validate(
            {
                "operations": [
                    {"op": "scale", "columns": ["Mold_Temperature_12"]}
                ],
                "planner_comment": "수치형 컬럼을 표준화합니다.",
            }
        )
    except ValidationError as exc:
        return exc
    raise AssertionError("expected PreprocessPlan validation to fail")


def test_preprocess_plan_validation_error_becomes_failed_output() -> None:
    result = _build_preprocess_plan_failed_output(_scale_method_validation_error())

    assert result["preprocess_result"]["status"] == "failed"
    assert result["preprocess_result"]["applied_ops_count"] == 0
    assert result["preprocess_result"]["error_stage"] == "preprocess_plan"
    assert "scale.method" not in result["preprocess_result"]["error"]
    assert "scale.method" in result["workflow_error"]["diagnostic_message"]
    assert result["workflow_error"]["error_code"] == "structured_output_validation"
    assert result["output"]["type"] == "preprocess_failed"
    assert "전처리 계획 형식" in result["output"]["content"]
    assert result["pending_approval"] == {}
    assert result["approved_plan"] == {}


def test_route_after_preprocess_planner_sends_failed_plan_to_failed_node() -> None:
    route = _route_after_preprocess_planner(
        {"preprocess_result": {"status": "failed"}}
    )

    assert route == "failed"


def test_route_after_preprocess_planner_sends_valid_plan_to_approval() -> None:
    route = _route_after_preprocess_planner(
        {"preprocess_plan": {"operations": [], "planner_comment": ""}}
    )

    assert route == "approval"


def test_preprocess_execution_error_keeps_public_stage_and_internal_diagnostic() -> None:
    result = execute_preprocess_plan(
        source_id="source-1",
        preprocess_plan={
            "operations": [
                {
                    "op": "scale",
                    "columns": ["Clamp_Open_Position"],
                    "method": "standardize",
                }
            ],
            "planner_comment": "수치형 컬럼을 표준화합니다.",
        },
        approved_plan=None,
        dataset_profile={},
        preprocess_service=cast(Any, _FailingPreprocessService()),
    )

    workflow_error = result["workflow_error"]
    public_error = result["output"]["public_error"]

    assert workflow_error["stage"] == "preprocess_execute"
    assert workflow_error["source"] == "preprocess_executor"
    assert workflow_error["error_code"] == "preprocess_execution_failed"
    assert "Column not found: Clamp_Open_Position" in workflow_error["diagnostic_message"]
    assert result["preprocess_result"]["error_stage"] == "preprocess_execute"
    assert public_error["error_stage"] == "preprocess_execute"
    assert "전처리 실행 중" in public_error["message"]
    assert "Column not found" not in public_error["message"]
