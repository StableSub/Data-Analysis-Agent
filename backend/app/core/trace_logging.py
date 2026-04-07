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


def log_trace(*, layer: str, event: str, payload: dict[str, Any], stage: str | None = None) -> None:
    context = get_trace_context()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "trace_id": context["trace_id"],
        "session_id": context["session_id"],
        "run_id": context["run_id"],
        "layer": layer,
        "event": event,
        "stage": stage if stage is not None else context["stage"],
        "payload": _to_serializable(payload),
    }

    TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False, default=str)
    with _WRITE_LOCK:
        with TRACE_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
