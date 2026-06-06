from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from ...orchestration.error_contract import (
    build_failure_output,
    build_workflow_error_from_exception,
    public_message_for_stage,
)
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
        message = "source_id가 없어 전처리를 실행하지 못했습니다."
        workflow_error = build_workflow_error_from_exception(
            stage="preprocess_execute",
            error_code="missing_source_id",
            source="preprocess_executor",
            output_type="preprocess_failed",
            retryable=False,
            exc=ValueError("source_id is required"),
            safe_message=message,
        )
        return {
            "workflow_error": workflow_error,
            "preprocess_result": {
                "status": "failed",
                "summary": message,
                "applied_ops_count": 0,
                "error": message,
                "error_stage": "preprocess_execute",
            },
            "output": build_failure_output(workflow_error),
        }

    try:
        plan = PreprocessPlan.model_validate(approved_plan or preprocess_plan or {})
    except ValidationError as exc:
        workflow_error = build_workflow_error_from_exception(
            stage="preprocess_plan",
            error_code="structured_output_validation",
            source="preprocess_executor",
            output_type="preprocess_failed",
            retryable=True,
            exc=exc,
        )
        message = workflow_error["safe_message"]
        return {
            "workflow_error": workflow_error,
            "preprocess_result": {
                "status": "failed",
                "summary": message,
                "applied_ops_count": 0,
                "error": message,
                "error_stage": "preprocess_plan",
            },
            "output": build_failure_output(workflow_error),
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
        workflow_error = build_workflow_error_from_exception(
            stage="preprocess_execute",
            error_code="preprocess_execution_failed",
            source="preprocess_executor",
            output_type="preprocess_failed",
            retryable=True,
            exc=exc,
            safe_message=public_message_for_stage("preprocess_execute"),
            details={"source_id": str(source_id)},
        )
        message = workflow_error["safe_message"]
        return {
            "workflow_error": workflow_error,
            "preprocess_result": {
                "status": "failed",
                "summary": message,
                "applied_ops_count": 0,
                "error": message,
                "error_stage": "preprocess_execute",
            },
            "revision_request": {},
            "approved_plan": {},
            "pending_approval": {},
            "output": build_failure_output(workflow_error),
        }

    updated_profile = dict(dataset_profile or {})
    updated_profile["preprocess_applied"] = True

    return {
        "source_id": apply_response.output_source_id,
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
