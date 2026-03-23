from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .planner import PreprocessPlan
from .service import PreprocessService


def execute_preprocess_plan(
    *,
    source_id: str | None,
    preprocess_plan: dict[str, Any] | None,
    approved_plan: dict[str, Any] | None,
    dataset_profile: dict[str, Any] | None,
    preprocess_service: PreprocessService,
) -> dict[str, Any]:
    if not source_id:
        return {
            "preprocess_result": {
                "status": "failed",
                "applied_ops_count": 0,
                "error": "source_id is required",
            }
        }

    try:
        plan = PreprocessPlan.model_validate(approved_plan or preprocess_plan or {})
    except ValidationError as exc:
        return {
            "preprocess_result": {
                "status": "failed",
                "applied_ops_count": 0,
                "error": f"invalid operation format: {exc}",
            }
        }

    if not plan.operations:
        return {
            "preprocess_result": {
                "status": "skipped",
                "applied_ops_count": 0,
            }
        }

    apply_response = preprocess_service.apply(source_id=str(source_id), operations=plan.operations)
    updated_profile = dict(dataset_profile or {})
    updated_profile["preprocess_applied"] = True

    return {
        "dataset_profile": updated_profile,
        "preprocess_result": {
            "status": "applied",
            "applied_ops_count": len(plan.operations),
            "input_source_id": apply_response.input_source_id,
            "output_source_id": apply_response.output_source_id,
            "output_filename": apply_response.output_filename,
        },
        "revision_request": {},
        "approved_plan": {},
        "pending_approval": {},
    }
