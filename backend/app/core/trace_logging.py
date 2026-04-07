from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TRACE_ID_VAR: ContextVar[str | None] = ContextVar("trace_id", default=None)
SESSION_ID_VAR: ContextVar[str | int | None] = ContextVar("session_id", default=None)
RUN_ID_VAR: ContextVar[str | None] = ContextVar("run_id", default=None)
STAGE_VAR: ContextVar[str | None] = ContextVar("workflow_stage", default=None)

TRACE_LOG_PATH = Path(__file__).resolve().parents[3] / "storage" / "logs" / "agent-trace.jsonl"
TRACE_SUMMARY_DIR = TRACE_LOG_PATH.parent / "traces"
_WRITE_LOCK = threading.Lock()
_MAX_LOG_STRING_LENGTH = 2000


def _truncate_string(value: str, *, max_length: int = _MAX_LOG_STRING_LENGTH) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[:max_length]}...<truncated>"


def _to_serializable(value: Any, *, path: tuple[str, ...] = ()) -> Any:
    if hasattr(value, "model_dump") and callable(value.model_dump):
        value = value.model_dump()

    if path and path[-1] == "image_base64":
        return "<omitted>"

    if isinstance(value, str):
        return _truncate_string(value)

    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text == "image_base64":
                result[key_text] = "<omitted>"
                continue

            next_value = _to_serializable(item, path=path + (key_text,))
            if key_text == "sample_rows" and isinstance(next_value, list):
                result[key_text] = next_value[:3]
            else:
                result[key_text] = next_value
        return result

    if isinstance(value, (list, tuple, set)):
        items = [_to_serializable(item, path=path) for item in value]
        if path and path[-1] == "sample_rows":
            return items[:3]
        return items

    if isinstance(value, Path):
        return str(value)

    if hasattr(value, "isoformat") and callable(value.isoformat):
        return value.isoformat()

    return _truncate_string(str(value))


def get_trace_context() -> dict[str, Any]:
    return {
        "trace_id": TRACE_ID_VAR.get(),
        "session_id": SESSION_ID_VAR.get(),
        "run_id": RUN_ID_VAR.get(),
        "stage": STAGE_VAR.get(),
    }


@contextmanager
def trace_context(
    *,
    trace_id: str | None = None,
    session_id: str | int | None = None,
    run_id: str | None = None,
    stage: str | None = None,
) -> Iterator[None]:
    tokens: list[tuple[ContextVar[Any], Any]] = []
    if trace_id is not None:
        tokens.append((TRACE_ID_VAR, TRACE_ID_VAR.set(trace_id)))
    if session_id is not None:
        tokens.append((SESSION_ID_VAR, SESSION_ID_VAR.set(session_id)))
    if run_id is not None:
        tokens.append((RUN_ID_VAR, RUN_ID_VAR.set(run_id)))
    if stage is not None:
        tokens.append((STAGE_VAR, STAGE_VAR.set(stage)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


def set_trace_stage(stage: str | None) -> None:
    STAGE_VAR.set(stage)


def _build_default_trace_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_id": entry["trace_id"],
        "session_id": entry["session_id"],
        "run_id": entry["run_id"],
        "status": "running",
        "question": None,
        "source_id": None,
        "started_at": entry["ts"],
        "updated_at": entry["ts"],
        "steps": [],
        "final_output": None,
        "error": None,
    }


def _get_trace_summary_path(trace_id: str) -> Path:
    return TRACE_SUMMARY_DIR / f"{trace_id}.json"


def _load_trace_summary(path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
    return _build_default_trace_summary(entry)


def _upsert_trace_step(
    summary: dict[str, Any],
    *,
    phase: str,
    layer: str,
    event: str,
    stage: str | None,
    status: str | None,
    message: str | None,
    ts: str,
    details: dict[str, Any] | None = None,
) -> None:
    steps = summary.setdefault("steps", [])
    if not isinstance(steps, list):
        steps = []
        summary["steps"] = steps

    step_payload = {
        "phase": phase,
        "layer": layer,
        "event": event,
        "stage": stage,
        "status": status,
        "message": message,
        "ts": ts,
        "details": details or {},
    }

    for index, existing in enumerate(steps):
        if isinstance(existing, dict) and existing.get("phase") == phase:
            steps[index] = step_payload
            return
    steps.append(step_payload)


def _extract_error_fields(payload: dict[str, Any]) -> dict[str, Any] | None:
    error_stage = payload.get("error_stage")
    error_message = payload.get("error_message")
    error_type = payload.get("error_type")

    if not any((error_stage, error_message, error_type)):
        return None

    return {
        "stage": error_stage,
        "message": error_message,
        "type": error_type,
    }


def _update_trace_summary(summary: dict[str, Any], entry: dict[str, Any]) -> None:
    layer = str(entry.get("layer") or "")
    event = str(entry.get("event") or "")
    stage = entry.get("stage")
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return

    ts = str(entry.get("ts") or "")
    summary["updated_at"] = ts
    if entry.get("session_id") is not None:
        summary["session_id"] = entry["session_id"]
    if entry.get("run_id") is not None:
        summary["run_id"] = entry["run_id"]

    if layer == "chat" and event == "ingress":
        summary["question"] = payload.get("question")
        summary["source_id"] = payload.get("source_id")
        _upsert_trace_step(
            summary,
            phase="ingress",
            layer=layer,
            event=event,
            stage=stage if isinstance(stage, str) else None,
            status="completed",
            message="질문을 수신했습니다.",
            ts=ts,
            details={
                "question": payload.get("question"),
                "source_id": payload.get("source_id"),
                "model_id": payload.get("model_id"),
            },
        )
        return

    if layer == "chat" and event == "resume_ingress":
        _upsert_trace_step(
            summary,
            phase="ingress",
            layer=layer,
            event=event,
            stage=stage if isinstance(stage, str) else None,
            status="completed",
            message="승인 이후 실행을 재개했습니다.",
            ts=ts,
            details={
                "decision": payload.get("decision"),
                "stage": payload.get("stage"),
                "instruction": payload.get("instruction"),
            },
        )
        return

    if layer == "chat" and event == "thought":
        step = payload.get("step")
        if not isinstance(step, dict):
            return
        phase = str(step.get("phase") or stage or "unknown")
        _upsert_trace_step(
            summary,
            phase=phase,
            layer=layer,
            event=event,
            stage=stage if isinstance(stage, str) else None,
            status=str(step.get("status") or ""),
            message=str(
                step.get("detail_message")
                or step.get("message")
                or step.get("display_message")
                or ""
            ),
            ts=ts,
            details={
                "display_message": step.get("display_message"),
                "audience": step.get("audience"),
            },
        )
        return

    if layer == "chat" and event == "approval_required":
        summary["status"] = "approval_required"
        pending_stage = str(payload.get("pending_stage") or "")
        approval_phase = f"{pending_stage}_approval" if pending_stage else "approval"
        _upsert_trace_step(
            summary,
            phase=approval_phase,
            layer=layer,
            event=event,
            stage=stage if isinstance(stage, str) else None,
            status="waiting",
            message="승인 대기 중입니다.",
            ts=ts,
            details={
                "pending_stage": pending_stage,
                "thought_step_count": payload.get("thought_step_count"),
            },
        )
        return

    if layer == "workflow" and event in {"snapshot", "workflow_final_state"}:
        final_status = payload.get("final_status")
        if final_status == "fail":
            summary["status"] = "fail"
        elif final_status == "success":
            summary["status"] = "success"

        summary_error = _extract_error_fields(payload)
        if summary_error is not None:
            summary["error"] = summary_error
        elif final_status == "success":
            summary["error"] = None
        return

    if layer == "chat" and event == "done":
        if payload.get("error_message"):
            summary["status"] = "fail"
        elif summary.get("status") != "fail":
            summary["status"] = "success"
        summary["final_output"] = {
            "answer": payload.get("answer"),
            "output_type": payload.get("output_type"),
        }
        summary_error = _extract_error_fields(payload)
        if summary_error is not None:
            summary["error"] = summary_error
        elif summary.get("status") == "success":
            summary["error"] = None
        _upsert_trace_step(
            summary,
            phase="done",
            layer=layer,
            event=event,
            stage=stage if isinstance(stage, str) else None,
            status=summary.get("status"),
            message=str(payload.get("answer") or ""),
            ts=ts,
            details={
                "output_type": payload.get("output_type"),
                "analysis_execution_status": payload.get("analysis_execution_status"),
                "preprocess_status": payload.get("preprocess_status"),
                "visualization_status": payload.get("visualization_status"),
            },
        )


def log_trace(*, layer: str, event: str, payload: dict[str, Any], stage: str | None = None) -> None:
    context = get_trace_context()
    serialized_payload = _to_serializable(payload)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "trace_id": context["trace_id"],
        "session_id": context["session_id"],
        "run_id": context["run_id"],
        "layer": layer,
        "event": event,
        "stage": stage if stage is not None else context["stage"],
        "payload": serialized_payload,
    }

    TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, default=str)
    with _WRITE_LOCK:
        with TRACE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
        trace_id = entry.get("trace_id")
        if isinstance(trace_id, str) and trace_id:
            summary_path = _get_trace_summary_path(trace_id)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary = _load_trace_summary(summary_path, entry)
            _update_trace_summary(summary, entry)
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
