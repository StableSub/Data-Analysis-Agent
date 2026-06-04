from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Dict

DEFAULT_PUBLIC_ERROR_MESSAGE = "요청을 처리하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

_STAGE_PUBLIC_MESSAGES: dict[str, str] = {
    "question_understanding": "질문을 이해하는 중 오류가 발생했습니다. 질문을 조금 더 구체적으로 다시 입력해 주세요.",
    "plan_validation": "분석 계획을 확인하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "preprocess_plan": "전처리 계획 형식이 올바르지 않습니다.",
    "analysis": "분석 단계에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "code_generation": "분석 코드를 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    "code_validation": "분석 코드를 검증하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
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
    return {
        "stage": stage_text,
        "error_code": str(error_code or "unknown_error"),
        "source": str(source or "unknown"),
        "output_type": str(output_type or "error"),
        "retryable": bool(retryable),
        "safe_message": message,
        "diagnostic_message": str(diagnostic_message or "")[:4000],
        "details": dict(details or {}),
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
    safe_message = _safe_message_for_stage(
        stage,
        safe_message=workflow_error.get("safe_message") if isinstance(workflow_error.get("safe_message"), str) else None,
    )
    return {
        "stage": stage,
        "error_stage": stage,
        "error_code": str(workflow_error.get("error_code") or "unknown_error"),
        "retryable": bool(workflow_error.get("retryable", False)),
        "message": safe_message,
        "error_message": safe_message,
        "output_type": str(workflow_error.get("output_type") or "error"),
    }


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
