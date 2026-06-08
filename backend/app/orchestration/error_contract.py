from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Dict

DEFAULT_PUBLIC_ERROR_MESSAGE = "요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
ANALYSIS_REPAIR_FAILED_STAGE = "analysis_repair_failed"
ANALYSIS_REPAIR_FAILED_MESSAGE = (
    "분석 코드를 자동으로 수정했지만 실행 가능한 형태로 만들지 못했습니다. "
    "질문 범위나 기준 컬럼을 좁혀 다시 실행해 주세요."
)
_INTERNAL_ANALYSIS_STAGES = {"code_validation"}
_ACTIONABLE_ANALYSIS_STAGES = {
    "planning_failed",
    "plan_validation",
    "sandbox_execution",
    "result_validation",
    ANALYSIS_REPAIR_FAILED_STAGE,
}
_PUBLIC_DETAIL_KEYS = {
    "stage_label",
    "failed_column",
    "operation",
    "reason_summary",
    "suggested_action",
}
_DEFAULT_ACTIONABLE_ANALYSIS_DETAILS: dict[str, dict[str, str]] = {
    "sandbox_execution": {
        "stage_label": "분석 코드 실행",
        "operation": "분석",
        "reason_summary": "생성된 분석 코드가 현재 데이터 조건이나 실행 환경에서 정상 종료되지 않았습니다.",
        "suggested_action": "대상 컬럼, 결측값, 숫자/날짜 형식을 확인해 주세요.",
    },
    "result_validation": {
        "stage_label": "분석 결과 검증",
        "operation": "분석 결과 검증",
        "reason_summary": "실행 결과가 분석 응답 계약과 맞지 않아 답변으로 확정할 수 없습니다.",
        "suggested_action": "대상 컬럼, 집계 기준, 결측값/숫자 형식을 확인해 주세요.",
    },
}

_STAGE_PUBLIC_MESSAGES: dict[str, str] = {
    "question_understanding": "질문을 이해하는 중 오류가 발생했습니다. 질문을 조금 더 구체적으로 다시 입력해 주세요.",
    "plan_validation": "분석 계획을 만들 수 없습니다. 질문의 분석 목표, 기준 컬럼, 집계 기준이 현재 데이터와 맞지 않습니다. 전처리만 확인하려면 전처리 결과를 확인하고, 분석을 다시 실행하려면 지표와 기준 컬럼을 지정해 주세요.",
    "preprocess_plan": "전처리 계획 형식이 올바르지 않습니다.",
    "preprocess_execute": "전처리 실행 중 일부 계획이 현재 데이터 컬럼과 맞지 않습니다. 전처리 계획의 중복 컬럼이나 이미 제거된 컬럼을 확인해 주세요.",
    "analysis": "분석 단계에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "code_generation": "분석 코드를 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "code_validation": ANALYSIS_REPAIR_FAILED_MESSAGE,
    ANALYSIS_REPAIR_FAILED_STAGE: ANALYSIS_REPAIR_FAILED_MESSAGE,
    "sandbox_execution": "분석 코드를 실행하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "result_validation": "분석 결과를 검증하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "persist_result": "분석 결과를 저장하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "visualization": "시각화 계획을 확인하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "report": "리포트 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "server_error": "서버에서 요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
}

_INTERNAL_KEYS = {
    "workflow_error",
    "diagnostic_message",
    "details",
    "schema_name",
    "field_path",
    "stderr",
    "input_value",
    "input_type",
}
_RAW_ERROR_MARKERS = (
    "validation error for",
    "Field required",
    "input_value",
    "input_type",
    "pydantic.dev",
    "Traceback (most recent call last)",
    "File \"",
    "diagnostic_message",
    "schema_name",
)
_SCHEMA_NAME_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]*(?:Error|Result|Payload|Understanding|Plan)\b")


def build_workflow_error(
    *,
    stage: str,
    error_code: str,
    source: str,
    output_type: str,
    retryable: bool,
    diagnostic_message: str = "",
    details: Mapping[str, Any] | None = None,
    safe_message: str | None = None,
) -> Dict[str, Any]:
    stage_text = str(stage or "unknown")
    message = _safe_message_for_stage(stage_text, safe_message=safe_message)
    diagnostic_details = dict(details or {})
    if is_internal_analysis_stage(stage_text):
        diagnostic_details.setdefault("internal_stage", stage_text)
    return {
        "stage": stage_text,
        "error_code": str(error_code or "unknown_error"),
        "source": str(source or "unknown"),
        "output_type": str(output_type or "error"),
        "retryable": bool(retryable),
        "safe_message": message,
        "diagnostic_message": str(diagnostic_message or "")[:4000],
        "details": diagnostic_details,
    }


def build_workflow_error_from_exception(
    *,
    stage: str,
    error_code: str,
    source: str,
    output_type: str,
    retryable: bool,
    exc: BaseException,
    safe_message: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    diagnostic_details = {
        "exception_type": type(exc).__name__,
        **dict(details or {}),
    }
    return build_workflow_error(
        stage=stage,
        error_code=error_code,
        source=source,
        output_type=output_type,
        retryable=retryable,
        safe_message=safe_message,
        diagnostic_message=str(exc),
        details=diagnostic_details,
    )


def to_public_error(workflow_error: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(workflow_error, Mapping):
        workflow_error = {}
    stage = str(workflow_error.get("stage") or "unknown")
    public_stage = public_stage_for_analysis_failure(stage)
    public_error_code = str(workflow_error.get("error_code") or "unknown_error")
    if public_stage != stage:
        public_error_code = public_stage
        safe_message = public_message_for_analysis_failure(stage)
    else:
        safe_message = _safe_message_for_stage(
            stage,
            safe_message=workflow_error.get("safe_message") if isinstance(workflow_error.get("safe_message"), str) else None,
        )
    details = workflow_error.get("details")
    public_details = _safe_public_error_details(
        details if isinstance(details, Mapping) else {}
    )
    if not public_details:
        public_details = _default_actionable_analysis_details(public_stage)
    if public_details and public_stage in _ACTIONABLE_ANALYSIS_STAGES:
        safe_message = _actionable_analysis_message(
            stage=public_stage,
            fallback_message=safe_message,
            details=public_details,
        )

    public_error = {
        "stage": public_stage,
        "error_stage": public_stage,
        "error_code": public_error_code,
        "source": str(workflow_error.get("source") or "unknown"),
        "retryable": bool(workflow_error.get("retryable", False)),
        "message": safe_message,
        "error_message": safe_message,
        "output_type": str(workflow_error.get("output_type") or "error"),
    }
    public_error.update(public_details)
    return public_error


def build_failure_output(workflow_error: Mapping[str, Any]) -> Dict[str, Any]:
    public_error = to_public_error(workflow_error)
    return {
        "type": public_error["output_type"],
        "content": public_error["message"],
        "public_error": public_error,
    }


def sanitize_public_payload(
    value: Any,
    *,
    fallback_message: str = DEFAULT_PUBLIC_ERROR_MESSAGE,
) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text in _INTERNAL_KEYS:
                continue
            sanitized[key_text] = sanitize_public_payload(
                item,
                fallback_message=fallback_message,
            )
        return sanitized
    if isinstance(value, str):
        return sanitize_public_message(value, fallback_message=fallback_message)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [
            sanitize_public_payload(item, fallback_message=fallback_message)
            for item in value
        ]
    return value


def sanitize_public_message(
    value: str,
    *,
    fallback_message: str = DEFAULT_PUBLIC_ERROR_MESSAGE,
) -> str:
    text = str(value or "").strip()
    if not text:
        return fallback_message
    if _looks_internal_error_text(text):
        return fallback_message
    return text


def public_message_for_stage(stage: str, *, fallback: str | None = None) -> str:
    return _safe_message_for_stage(stage, safe_message=fallback)


def is_internal_analysis_stage(stage: str) -> bool:
    return str(stage or "") in _INTERNAL_ANALYSIS_STAGES


def public_stage_for_analysis_failure(stage: str) -> str:
    if is_internal_analysis_stage(stage):
        return ANALYSIS_REPAIR_FAILED_STAGE
    return str(stage or "unknown")


def public_message_for_analysis_failure(stage: str) -> str:
    if is_internal_analysis_stage(stage):
        return ANALYSIS_REPAIR_FAILED_MESSAGE
    return public_message_for_stage(stage)


def _safe_message_for_stage(stage: str, *, safe_message: str | None = None) -> str:
    if safe_message and not _looks_internal_error_text(safe_message):
        return safe_message.strip()
    return _STAGE_PUBLIC_MESSAGES.get(stage, DEFAULT_PUBLIC_ERROR_MESSAGE)


def _looks_internal_error_text(text: str) -> bool:
    if any(marker in text for marker in _RAW_ERROR_MARKERS):
        return True
    if "validation error" in text.lower() and _SCHEMA_NAME_RE.search(text):
        return True
    return False


def _safe_public_error_details(details: Mapping[str, Any]) -> Dict[str, str]:
    safe_details: Dict[str, str] = {}
    for key in _PUBLIC_DETAIL_KEYS:
        value = details.get(key)
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or _looks_internal_error_text(cleaned):
            continue
        safe_details[key] = cleaned[:300]
    return safe_details


def _default_actionable_analysis_details(stage: str) -> dict[str, str]:
    return dict(_DEFAULT_ACTIONABLE_ANALYSIS_DETAILS.get(stage, {}))


def _actionable_analysis_message(
    *,
    stage: str,
    fallback_message: str,
    details: Mapping[str, str],
) -> str:
    failed_column = details.get("failed_column")
    operation = details.get("operation")
    reason_summary = details.get("reason_summary")
    suggested_action = details.get("suggested_action")
    stage_label = details.get("stage_label") or stage

    if not (failed_column or operation or reason_summary or suggested_action):
        return fallback_message

    target = failed_column or "요청한 분석 대상"
    action = operation or "분석"
    reason = reason_summary or "현재 데이터 조건이 분석 결과 계약과 맞지 않습니다."
    suggestion = (
        suggested_action
        or "대상 컬럼과 기준 컬럼을 확인한 뒤 질문 범위를 좁혀 다시 실행해 주세요."
    )
    message = (
        f"{target} {action}을 {stage_label} 단계에서 완료하지 못했습니다. "
        f"{reason} {suggestion}"
    )
    return sanitize_public_message(message, fallback_message=fallback_message)
