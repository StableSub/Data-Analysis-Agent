from __future__ import annotations

from pydantic import ValidationError

from backend.app.modules.preprocess.planner import PreprocessPlan
from backend.app.orchestration.workflows.preprocess import (
    _build_preprocess_plan_failed_output,
    _route_after_preprocess_planner,
)


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
