from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, Dict, cast

from backend.app.core.trace_logging import _extract_error_fields, _update_trace_summary
from backend.app.modules.chat import service as chat_service_module
from backend.app.modules.chat.service import ChatService
from backend.app.orchestration.client import AgentClient


def _collect(coro_or_agen: Any) -> list[Dict[str, Any]]:
    async def _run() -> list[Dict[str, Any]]:
        return [event async for event in coro_or_agen]

    return asyncio.run(_run())


def _make_agent(snapshots: list[Dict[str, Any]]) -> AgentClient:
    class FakeWorkflow:
        async def astream(self, input_payload: Any, config: Any, *, stream_mode: str):
            for snapshot in snapshots:
                yield snapshot

    @asynccontextmanager
    async def fake_runtime():
        yield SimpleNamespace(workflow=FakeWorkflow())

    return AgentClient(workflow_runtime_factory=fake_runtime)


def _serialized(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def test_error_event_includes_public_correlation_fields_without_diagnostics() -> None:
    agent = _make_agent(
        [
            {
                "final_status": "fail",
                "workflow_error": {
                    "stage": "sandbox_execution",
                    "error_code": "analysis_execution_failed",
                    "source": "analysis_validation",
                    "output_type": "analysis_failed",
                    "retryable": True,
                    "safe_message": "분석 코드를 실행하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
                    "diagnostic_message": "summary: Input should be a valid string",
                    "details": {"error_type": "invalid_json", "field_path": "summary"},
                },
            }
        ]
    )

    events = _collect(agent.astream_with_trace(session_id="1", question="불량 사유별 건수"))
    error = next(event for event in events if event.get("type") == "error")

    assert error["error_stage"] == "sandbox_execution"
    assert error["error_code"] == "analysis_execution_failed"
    assert error["error_source"] == "analysis_validation"
    assert error["public_error"]["source"] == "analysis_validation"
    public_text = _serialized(error)
    assert "diagnostic_message" not in public_text
    assert "Input should be a valid string" not in public_text
    assert "field_path" not in public_text


def test_trace_summary_error_fields_include_diagnostic_cause() -> None:
    fields = _extract_error_fields(
        {
            "error_stage": "sandbox_execution",
            "error_message": "분석 코드를 실행하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "error_type": "invalid_json",
            "error_source": "analysis_validation",
            "diagnostic_message": "summary: Input should be a valid string",
        }
    )

    assert fields == {
        "stage": "sandbox_execution",
        "message": "분석 코드를 실행하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        "type": "invalid_json",
        "source": "analysis_validation",
        "diagnostic_message": "summary: Input should be a valid string",
    }


def test_chat_error_trace_summary_records_source_and_diagnostic_cause() -> None:
    summary: Dict[str, Any] = {
        "trace_id": "trace-1",
        "session_id": None,
        "run_id": "run-1",
        "status": "running",
        "question": None,
        "source_id": None,
        "started_at": "2026-06-06T00:00:00+00:00",
        "updated_at": "2026-06-06T00:00:00+00:00",
        "steps": [],
        "final_output": None,
        "error": None,
    }

    _update_trace_summary(
        summary,
        {
            "layer": "chat",
            "event": "invalid_source_id",
            "stage": None,
            "ts": "2026-06-06T00:00:01+00:00",
            "payload": {
                "source_id": "missing-source",
                "error_stage": "dataset_resolution",
                "error_message": "요청한 데이터셋을 찾을 수 없습니다.",
                "error_type": "invalid_source_id",
                "error_source": "chat_source_validation",
                "diagnostic_message": "dataset source_id not found: missing-source",
            },
        },
    )

    assert summary["status"] == "fail"
    assert summary["source_id"] == "missing-source"
    assert summary["error"] == {
        "stage": "dataset_resolution",
        "message": "요청한 데이터셋을 찾을 수 없습니다.",
        "type": "invalid_source_id",
        "source": "chat_source_validation",
        "diagnostic_message": "dataset source_id not found: missing-source",
    }
    assert summary["steps"][0]["phase"] == "dataset_resolution"
    assert summary["steps"][0]["status"] == "failed"


def test_chat_stream_exception_keeps_trace_id_and_logs_diagnostic(
    monkeypatch: Any,
) -> None:
    captured_logs: list[Dict[str, Any]] = []

    def capture_log_trace(**kwargs: Any) -> None:
        captured_logs.append(kwargs)

    monkeypatch.setattr(chat_service_module, "log_trace", capture_log_trace)

    class ExplodingAgent:
        async def astream_with_trace(self, **_: Any):
            yield {
                "type": "thought",
                "step": {
                    "phase": "guideline",
                    "message": "guideline lookup started",
                    "status": "active",
                },
            }
            raise RuntimeError("guideline source not found: guideline-1")

    class Repository:
        def get_session(self, session_id: int) -> Any:
            return SimpleNamespace(id=session_id, title="session", messages=[])

        def create_session(self, title: str) -> Any:
            return SimpleNamespace(id=1, title=title, messages=[])

        def append_message(self, session: Any, role: str, content: str) -> None:
            session.messages.append(SimpleNamespace(role=role, content=content))

    class DatasetRepository:
        def get_by_source_id(self, source_id: str) -> Any:
            return SimpleNamespace(source_id=source_id, storage_path="dataset.csv")

    service = ChatService(
        agent=cast(Any, ExplodingAgent()),
        repository=cast(Any, Repository()),
        dataset_repository=cast(Any, DatasetRepository()),
    )

    events = _collect(
        service.ask_stream(
            question="왜 불량이 났어?",
            session_id=1,
            source_id="dataset-1",
            trace_id="trace-stream-error",
        )
    )

    error = events[-1]
    assert error["event"] == "error"
    assert error["data"]["trace_id"] == "trace-stream-error"
    assert error["data"]["session_id"] == 1
    assert error["data"]["stage"] == "server_error"
    assert error["data"]["error_source"] == "chat_stream"
    assert error["data"]["error_code"] == "server_error"
    assert "guideline source not found" not in _serialized(error)

    stream_exception_log = next(
        item for item in captured_logs if item.get("event") == "stream_exception"
    )
    assert stream_exception_log["payload"]["trace_id"] == "trace-stream-error"
    assert stream_exception_log["payload"]["error_type"] == "RuntimeError"
    assert (
        stream_exception_log["payload"]["diagnostic_message"]
        == "guideline source not found: guideline-1"
    )
