from __future__ import annotations

import json
import importlib.util
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import pytest

pytestmark = pytest.mark.live_benchmark


@dataclass(frozen=True)
class SseEvent:
    name: str
    data: dict[str, Any]


def _live_chat_gate_enabled() -> bool:
    return os.environ.get("RUN_LIVE_CHAT_STREAM_GATE") == "1"


def _require_live_chat_gate() -> None:
    if os.environ.get("RUN_LIVE_BENCHMARK") != "1":
        pytest.skip("set RUN_LIVE_BENCHMARK=1 to run opt-in live benchmark tests")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live LLM workflow benchmark runs")
    if importlib.util.find_spec("langchain_openai") is None:
        pytest.skip("langchain-openai is required for live LLM workflow benchmark runs")
    if not _live_chat_gate_enabled():
        pytest.skip("set RUN_LIVE_CHAT_STREAM_GATE=1 to run the real /chats/stream HTTP gate")


def _live_timeout_seconds() -> float:
    return float(os.environ.get("BENCHMARK_LIVE_TIMEOUT_SECONDS", "120"))


def _parse_sse_events(raw_body: str) -> list[SseEvent]:
    events: list[SseEvent] = []
    for block in raw_body.split("\n\n"):
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        if not data_lines:
            continue
        events.append(SseEvent(name=event_name, data=json.loads("\n".join(data_lines))))
    return events


def _post_chat_stream(*, base_url: str, payload: dict[str, Any]) -> tuple[int, str]:
    request = Request(
        f"{base_url.rstrip('/')}/chats/stream",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=_live_timeout_seconds()) as response:
            return response.status, response.read().decode("utf-8")
    except URLError as exc:
        raise AssertionError(f"live /chats/stream gate could not reach server: {exc}") from exc


def test_chat_stream_daily_defects_live_gate() -> None:
    # Given: the real backend server is already running with the same dataset/guideline
    # state used by the user-facing Workbench flow.
    _require_live_chat_gate()
    payload = {
        "session_id": int(os.environ.get("CHAT_STREAM_LIVE_SESSION_ID", "1")),
        "source_id": os.environ.get(
            "CHAT_STREAM_LIVE_SOURCE_ID",
            "f309892b-9a32-46a0-af75-03b0eaef6e5e",
        ),
        "guideline_source_id": os.environ.get(
            "CHAT_STREAM_LIVE_GUIDELINE_SOURCE_ID",
            "f3a99d9f-c81d-497a-a590-287e94b8c91c",
        ),
        "question": os.environ.get(
            "CHAT_STREAM_LIVE_QUESTION",
            "날짜별 불량 건수를 분석해줘.",
        ),
        "model_id": os.environ.get("CHAT_STREAM_LIVE_MODEL_ID", "gpt-5-nano"),
    }

    # When: the chat question is submitted through the public SSE route.
    status_code, raw_body = _post_chat_stream(
        base_url=os.environ.get("CHAT_STREAM_LIVE_BASE_URL", "http://127.0.0.1:8021"),
        payload=payload,
    )

    # Then: the normal workflow returns a successful data answer without hiding
    # failures behind the fast path or leaking analysis_validation/result_validation.
    events = _parse_sse_events(raw_body)
    error_events = [event for event in events if event.name == "error"]
    done_events = [event for event in events if event.name == "done"]

    assert status_code == 200
    assert error_events == []
    assert done_events, raw_body
    done = done_events[-1].data
    serialized_done = json.dumps(done, ensure_ascii=False, sort_keys=True)
    assert done.get("status") == "success"
    assert done.get("output_type") == "data_qa"
    assert "result_validation" not in serialized_done
    assert "analysis_validation" not in serialized_done
