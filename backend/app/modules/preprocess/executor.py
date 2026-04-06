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
    def _build_failed_output(message: str) -> dict[str, Any]:
        return {
            "type": "preprocess_failed",
            "content": message,
        }

    if not source_id:
        message = "source_id가 없어 전처리를 실행하지 못했습니다."
        return {
            "preprocess_result": {
                "status": "failed",
                "summary": message,
                "applied_ops_count": 0,
                "error": "source_id is required",
            },
            "output": _build_failed_output(message),
        }

    try:
        plan = PreprocessPlan.model_validate(approved_plan or preprocess_plan or {})
    except ValidationError as exc:
        message = "전처리 계획 형식이 올바르지 않습니다."
        return {
            "preprocess_result": {
                "status": "failed",
                "summary": message,
                "applied_ops_count": 0,
                "error": f"invalid operation format: {exc}",
            },
            "output": _build_failed_output(message),
        }

    if not plan.operations:
        return {
            "preprocess_result": {
                "status": "skipped",
                "summary": "전처리 없이 다음 단계로 진행했습니다.",
                "applied_ops_count": 0,
            }
        }

    try:
        apply_response = preprocess_service.apply(source_id=str(source_id), operations=plan.operations)
    except (FileNotFoundError, ValueError) as exc:
        message = f"전처리 단계에서 오류가 발생했습니다: {exc}"
        return {
            "preprocess_result": {
                "status": "failed",
                "summary": message,
                "applied_ops_count": 0,
                "error": str(exc),
            },
            "revision_request": {},
            "approved_plan": {},
            "pending_approval": {},
            "output": _build_failed_output(message),
        }

    updated_profile = dict(dataset_profile or {})
    updated_profile["preprocess_applied"] = True

    return {
        "dataset_profile": updated_profile,
        "preprocess_result": {
            "status": "applied",
            "summary": f"전처리 연산 {len(plan.operations)}개를 적용했습니다.",
            "applied_ops_count": len(plan.operations),
            "input_source_id": apply_response.input_source_id,
            "output_source_id": apply_response.output_source_id,
            "output_filename": apply_response.output_filename,
        },
        "revision_request": {},
        "approved_plan": {},
        "pending_approval": {},
    }
