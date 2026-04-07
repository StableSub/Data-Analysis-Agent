from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from backend.app.core import trace_logging
from backend.app.orchestration.client import AgentClient


class TraceLoggingTests(unittest.TestCase):
    def _patched_trace_paths(self, root: Path) -> ExitStack:
        stack = ExitStack()
        trace_log_path = root / "logs" / "agent-trace.jsonl"
        trace_summary_dir = root / "logs" / "traces"
        stack.enter_context(patch.object(trace_logging, "TRACE_LOG_PATH", trace_log_path))
        stack.enter_context(patch.object(trace_logging, "TRACE_SUMMARY_DIR", trace_summary_dir))
        return stack

    def test_agent_client_snapshot_includes_error_fields(self) -> None:
        snapshot = {
            "final_status": "fail",
            "analysis_error": {
                "stage": "plan_validation",
                "message": "metric requires a source column",
                "detail": {"exception_type": "ValueError"},
            },
            "analysis_result": {
                "execution_status": "fail",
                "error_stage": "plan_validation",
                "error_message": "metric requires a source column",
            },
        }

        summary = AgentClient._summarize_snapshot(snapshot)

        self.assertEqual(summary["error_stage"], "plan_validation")
        self.assertEqual(summary["error_message"], "metric requires a source column")
        self.assertEqual(summary["error_type"], "ValueError")

    def test_log_trace_writes_success_trace_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self._patched_trace_paths(root):
                with trace_logging.trace_context(
                    trace_id="trace-success",
                    session_id=7,
                    run_id="run-success",
                ):
                    trace_logging.log_trace(
                        layer="chat",
                        event="ingress",
                        payload={
                            "trace_id": "trace-success",
                            "session_id": 7,
                            "run_id": "run-success",
                            "source_id": "source-1",
                            "question": "결측치 현황을 알려줘",
                            "question_length": 12,
                            "model_id": "gpt-5-nano",
                        },
                    )
                    trace_logging.log_trace(
                        layer="chat",
                        event="thought",
                        payload={
                            "trace_id": "trace-success",
                            "step": {
                                "phase": "planning",
                                "message": "planner가 분석 경로를 선택했습니다.",
                                "detail_message": "planner가 분석 경로를 선택했습니다.",
                                "display_message": "분석 경로를 선택했습니다.",
                                "status": "completed",
                                "audience": "user",
                            },
                        },
                    )
                    trace_logging.log_trace(
                        layer="chat",
                        event="done",
                        payload={
                            "trace_id": "trace-success",
                            "answer": "결과를 준비했습니다.",
                            "output_type": "analysis",
                            "preprocess_status": None,
                            "analysis_execution_status": "success",
                            "visualization_status": None,
                            "pending_approval_stage": None,
                            "error_stage": None,
                            "error_message": None,
                            "error_type": None,
                        },
                    )

            summary_path = root / "logs" / "traces" / "trace-success.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "success")
            self.assertEqual(summary["question"], "결측치 현황을 알려줘")
            self.assertEqual(summary["source_id"], "source-1")
            self.assertEqual(summary["final_output"]["answer"], "결과를 준비했습니다.")
            self.assertIsNone(summary["error"])
            self.assertEqual(
                [step["phase"] for step in summary["steps"]],
                ["ingress", "planning", "done"],
            )

    def test_log_trace_writes_approval_trace_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self._patched_trace_paths(root):
                with trace_logging.trace_context(
                    trace_id="trace-approval",
                    session_id=3,
                    run_id="run-approval",
                ):
                    trace_logging.log_trace(
                        layer="chat",
                        event="approval_required",
                        payload={
                            "trace_id": "trace-approval",
                            "pending_stage": "preprocess",
                            "thought_step_count": 4,
                        },
                    )

            summary_path = root / "logs" / "traces" / "trace-approval.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(summary["status"], "approval_required")
            self.assertEqual(summary["steps"][0]["phase"], "preprocess_approval")
            self.assertEqual(summary["steps"][0]["status"], "waiting")

    def test_log_trace_writes_failure_trace_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self._patched_trace_paths(root):
                with trace_logging.trace_context(
                    trace_id="trace-fail",
                    session_id=9,
                    run_id="run-fail",
                ):
                    trace_logging.log_trace(
                        layer="workflow",
                        event="snapshot",
                        payload={
                            "handoff_next_step": "analysis",
                            "planning_route": "analysis",
                            "planning_preprocess_required": True,
                            "planning_need_visualization": False,
                            "planning_need_report": False,
                            "final_status": "fail",
                            "output_type": None,
                            "analysis_execution_status": "fail",
                            "visualization_status": None,
                            "report_status": None,
                            "error_stage": "plan_validation",
                            "error_message": "metric 'missing_rate' requires a source column",
                            "error_type": "ValueError",
                            "interrupt_stage": None,
                        },
                    )
                    trace_logging.log_trace(
                        layer="chat",
                        event="done",
                        payload={
                            "trace_id": "trace-fail",
                            "answer": "응답을 생성하지 못했습니다.",
                            "output_type": None,
                            "preprocess_status": "applied",
                            "analysis_execution_status": "fail",
                            "visualization_status": None,
                            "pending_approval_stage": None,
                            "error_stage": "plan_validation",
                            "error_message": "metric 'missing_rate' requires a source column",
                            "error_type": "ValueError",
                        },
                    )

            summary_path = root / "logs" / "traces" / "trace-fail.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            jsonl_path = root / "logs" / "agent-trace.jsonl"
            entries = [
                json.loads(line)
                for line in jsonl_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            self.assertEqual(summary["status"], "fail")
            self.assertEqual(summary["error"]["stage"], "plan_validation")
            self.assertEqual(
                summary["error"]["message"],
                "metric 'missing_rate' requires a source column",
            )
            self.assertEqual(summary["error"]["type"], "ValueError")
            self.assertEqual(entries[0]["payload"]["error_message"], "metric 'missing_rate' requires a source column")
            self.assertEqual(entries[1]["payload"]["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
