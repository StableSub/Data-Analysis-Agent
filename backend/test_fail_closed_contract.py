from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from backend.app.core import trace_logging
from backend.app.modules.chat.router import ask_chat_stream
from backend.app.modules.chat.schemas import ChatRequest
from backend.app.modules.chat.service import ChatService
from backend.app.orchestration.client import AgentClient
from backend.app.orchestration.workflows.report import build_report_workflow


async def _collect_stream(response: StreamingResponse) -> str:
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunks.append(chunk.decode("utf-8"))
        else:
            chunks.append(chunk)
    return "".join(chunks)


class _FakeChatIngressService:
    def __init__(self, *, has_dataset: bool = True) -> None:
        self._has_dataset = has_dataset
        self.checked_source_ids: list[str] = []
        self.ask_stream_calls: list[dict[str, object]] = []

    def has_dataset_source(self, source_id: str) -> bool:
        self.checked_source_ids.append(source_id)
        return self._has_dataset

    def ask_stream(self, **kwargs):
        self.ask_stream_calls.append(kwargs)

        async def iterator():
            yield {
                "event": "session",
                "data": {
                    "session_id": 1,
                    "run_id": "run-1",
                    "trace_id": "trace-1",
                },
            }
            yield {
                "event": "done",
                "data": {
                    "answer": "ok",
                    "session_id": 1,
                    "run_id": "run-1",
                    "trace_id": "trace-1",
                },
            }

        return iterator()


class _DraftFailReportService:
    def build_report_draft(self, **kwargs):
        raise RuntimeError("draft exploded")

    def save_report(self, **kwargs):
        raise AssertionError("save_report should not be called")


class _SaveFailReportService:
    def build_report_draft(self, **kwargs):
        return {
            "status": "generated",
            "summary": "report body",
            "metrics": {},
            "visualizations": [],
        }

    def save_report(self, **kwargs):
        raise RuntimeError("save exploded")


class _EmptyDraftReportService:
    def build_report_draft(self, **kwargs):
        return {
            "status": "generated",
            "summary": "",
            "metrics": {},
            "visualizations": [],
        }

    def save_report(self, **kwargs):
        raise AssertionError("save_report should not be called")


class _SuccessReportService:
    def build_report_draft(self, **kwargs):
        return {
            "status": "generated",
            "summary": "final report body",
            "metrics": {},
            "visualizations": [],
        }

    def save_report(self, **kwargs):
        return SimpleNamespace(id="report-1")


class _FakeChatRepository:
    def __init__(self) -> None:
        self.session = SimpleNamespace(id=11)
        self.appended_messages: list[tuple[int, str, str]] = []

    def get_session(self, session_id: int):
        if session_id == self.session.id:
            return self.session
        return None

    def create_session(self, title: str | None = None):
        return self.session

    def append_message(self, session, role: str, content: str):
        self.appended_messages.append((session.id, role, content))
        return SimpleNamespace(session_id=session.id, role=role, content=content)


class _FakeReportFailureAgent:
    def astream_with_trace(self, **kwargs):
        async def iterator():
            yield {
                "type": "done",
                "answer": "리포트 생성에 실패했습니다.",
                "thought_steps": [],
                "report_result": {
                    "status": "failed",
                    "summary": "리포트 생성에 실패했습니다.",
                    "error": "save exploded",
                },
                "output_type": "report_failed",
                "output": {
                    "type": "report_failed",
                    "content": "리포트 생성에 실패했습니다.",
                },
            }

        return iterator()


class FailClosedChatIngressTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_stream_rejects_missing_dataset_source_before_stream_starts(self) -> None:
        chat_service = _FakeChatIngressService(has_dataset=False)

        with self.assertRaises(HTTPException) as context:
            await ask_chat_stream(
                request=ChatRequest(question="hello", source_id="missing-source"),
                chat_service=chat_service,
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(chat_service.checked_source_ids, ["missing-source"])
        self.assertEqual(chat_service.ask_stream_calls, [])

    async def test_chat_stream_allows_blank_source_id_without_dataset_lookup(self) -> None:
        chat_service = _FakeChatIngressService(has_dataset=False)

        response = await ask_chat_stream(
            request=ChatRequest(question="hello", source_id=""),
            chat_service=chat_service,
        )

        self.assertIsInstance(response, StreamingResponse)
        body = await _collect_stream(response)
        self.assertIn("event: done", body)
        self.assertEqual(chat_service.checked_source_ids, [])
        self.assertEqual(len(chat_service.ask_stream_calls), 1)

    async def test_chat_stream_allows_existing_dataset_source(self) -> None:
        chat_service = _FakeChatIngressService(has_dataset=True)

        response = await ask_chat_stream(
            request=ChatRequest(question="hello", source_id="dataset-1"),
            chat_service=chat_service,
        )

        self.assertIsInstance(response, StreamingResponse)
        body = await _collect_stream(response)
        self.assertIn("event: done", body)
        self.assertEqual(chat_service.checked_source_ids, ["dataset-1"])
        self.assertEqual(chat_service.ask_stream_calls[0]["source_id"], "dataset-1")


class ReportWorkflowFailureTests(unittest.TestCase):
    def _base_state(self) -> dict[str, object]:
        return {
            "user_input": "report please",
            "session_id": "7",
            "dataset_context": {"source_id": "dataset-1", "filename": "dataset.csv"},
        }

    def test_report_workflow_marks_draft_generation_failure_as_report_failed(self) -> None:
        workflow = build_report_workflow(report_service=_DraftFailReportService())

        result = workflow.invoke(self._base_state())

        self.assertEqual(result["final_status"], "fail")
        self.assertEqual(result["report_result"]["status"], "failed")
        self.assertEqual(result["output"]["type"], "report_failed")
        self.assertEqual(result["report_result"]["error"], "draft exploded")

    def test_report_workflow_marks_save_failure_as_report_failed(self) -> None:
        with patch(
            "backend.app.orchestration.workflows.report.interrupt",
            return_value={"decision": "approve"},
        ):
            workflow = build_report_workflow(report_service=_SaveFailReportService())
            result = workflow.invoke(self._base_state())

        self.assertEqual(result["final_status"], "fail")
        self.assertEqual(result["report_result"]["status"], "failed")
        self.assertEqual(result["output"]["type"], "report_failed")
        self.assertEqual(result["report_result"]["error"], "save exploded")

    def test_report_workflow_marks_empty_draft_as_report_failed(self) -> None:
        with patch(
            "backend.app.orchestration.workflows.report.interrupt",
            return_value={"decision": "approve"},
        ):
            workflow = build_report_workflow(report_service=_EmptyDraftReportService())
            result = workflow.invoke(self._base_state())

        self.assertEqual(result["final_status"], "fail")
        self.assertEqual(result["report_result"]["status"], "failed")
        self.assertEqual(result["output"]["type"], "report_failed")
        self.assertEqual(result["report_result"]["error"], "REPORT_DRAFT_EMPTY")

    def test_report_workflow_keeps_report_answer_on_success(self) -> None:
        with patch(
            "backend.app.orchestration.workflows.report.interrupt",
            return_value={"decision": "approve"},
        ):
            workflow = build_report_workflow(report_service=_SuccessReportService())
            result = workflow.invoke(self._base_state())

        self.assertEqual(result["report_result"]["status"], "generated")
        self.assertEqual(result["output"]["type"], "report_answer")
        self.assertIsNone(result.get("final_status"))


class ReportFailureTraceTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_service_done_event_includes_report_failure_and_logs_report_error(self) -> None:
        repository = _FakeChatRepository()
        service = ChatService(
            agent=_FakeReportFailureAgent(),
            repository=repository,
            dataset_repository=SimpleNamespace(),
        )
        logged_done_payloads: list[dict[str, object]] = []

        def _capture_log_trace(*, layer, event, payload, stage=None):
            if layer == "chat" and event == "done":
                logged_done_payloads.append(payload)

        with patch("backend.app.modules.chat.service.log_trace", side_effect=_capture_log_trace):
            events = [event async for event in service.ask_stream(question="report please")]

        done_event = events[-1]
        self.assertEqual(done_event["event"], "done")
        self.assertEqual(done_event["data"]["report_result"]["status"], "failed")
        self.assertEqual(done_event["data"]["output_type"], "report_failed")
        self.assertEqual(logged_done_payloads[-1]["error_stage"], "report")
        self.assertEqual(logged_done_payloads[-1]["error_message"], "save exploded")
        self.assertEqual(logged_done_payloads[-1]["report_status"], "failed")

    def test_agent_client_snapshot_marks_report_failure(self) -> None:
        summary = AgentClient._summarize_snapshot(
            {
                "final_status": "fail",
                "report_result": {
                    "status": "failed",
                    "summary": "리포트 생성에 실패했습니다.",
                    "error": "save exploded",
                },
            }
        )

        self.assertEqual(summary["report_status"], "failed")
        self.assertEqual(summary["error_stage"], "report")
        self.assertEqual(summary["error_message"], "save exploded")

    def test_trace_summary_persists_report_failure_as_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            stack = ExitStack()
            trace_log_path = root / "logs" / "agent-trace.jsonl"
            trace_summary_dir = root / "logs" / "traces"
            stack.enter_context(patch.object(trace_logging, "TRACE_LOG_PATH", trace_log_path))
            stack.enter_context(patch.object(trace_logging, "TRACE_SUMMARY_DIR", trace_summary_dir))
            with stack:
                with trace_logging.trace_context(
                    trace_id="trace-report-fail",
                    session_id=5,
                    run_id="run-report-fail",
                ):
                    trace_logging.log_trace(
                        layer="workflow",
                        event="snapshot",
                        payload={
                            "handoff_next_step": "report",
                            "planning_route": "analysis",
                            "planning_preprocess_required": False,
                            "planning_need_visualization": False,
                            "planning_need_report": True,
                            "final_status": "fail",
                            "output_type": "report_failed",
                            "analysis_execution_status": "success",
                            "visualization_status": None,
                            "report_status": "failed",
                            "error_stage": "report",
                            "error_message": "save exploded",
                            "error_type": None,
                            "interrupt_stage": None,
                        },
                    )
                    trace_logging.log_trace(
                        layer="chat",
                        event="done",
                        payload={
                            "trace_id": "trace-report-fail",
                            "answer": "리포트 생성에 실패했습니다.",
                            "output_type": "report_failed",
                            "preprocess_status": None,
                            "analysis_execution_status": "success",
                            "visualization_status": None,
                            "report_status": "failed",
                            "pending_approval_stage": None,
                            "error_stage": "report",
                            "error_message": "save exploded",
                            "error_type": None,
                        },
                    )

            summary_path = root / "logs" / "traces" / "trace-report-fail.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "fail")
            self.assertEqual(summary["error"]["stage"], "report")
            self.assertEqual(summary["error"]["message"], "save exploded")
            self.assertEqual(summary["final_output"]["output_type"], "report_failed")


if __name__ == "__main__":
    unittest.main()
