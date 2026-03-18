from __future__ import annotations

import json
import unittest
from typing import Any

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.chat.dependencies import get_chat_service
from backend.app.modules.chat.schemas import PendingApprovalResponse


def _parse_sse_events(raw_text: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = ""
        payload: dict[str, Any] = {}
        for line in block.splitlines():
            if line.startswith("event: "):
                event_name = line[len("event: ") :].strip()
            elif line.startswith("data: "):
                payload = json.loads(line[len("data: ") :])
        if event_name:
            events.append((event_name, payload))
    return events


class FakeChatService:
    def __init__(self) -> None:
        self.pending = PendingApprovalResponse(
            session_id=1,
            run_id="run-approval",
            pending_approval={
                "stage": "preprocess",
                "kind": "plan_review",
                "title": "Preprocess plan review",
                "summary": "검토가 필요합니다.",
                "source_id": "source-1",
                "plan": {"operations": []},
                "draft": "",
                "review": {},
            },
        )

    async def ask_stream(
        self,
        *,
        question: str,
        session_id: int | None = None,
        model_id: str | None = None,
        source_id: str | None = None,
    ):
        if question == "approval":
            yield {"event": "session", "data": {"session_id": 1, "run_id": "run-approval"}}
            yield {
                "event": "approval_required",
                "data": {
                    "session_id": 1,
                    "run_id": "run-approval",
                    "pending_approval": self.pending.pending_approval.model_dump(),
                    "thought_steps": [
                        {
                            "phase": "analysis",
                            "message": "검토 단계로 이동했습니다.",
                            "status": "completed",
                        }
                    ],
                },
            }
            return

        yield {"event": "session", "data": {"session_id": 1, "run_id": "run-1"}}
        yield {
            "event": "thought",
            "data": {
                "phase": "analysis",
                "message": "질문을 해석했습니다.",
                "status": "completed",
            },
        }
        yield {"event": "chunk", "data": {"delta": "부분 응답"}}
        yield {
            "event": "done",
            "data": {
                "answer": "최종 응답",
                "session_id": 1,
                "run_id": "run-1",
                "thought_steps": [
                    {
                        "phase": "analysis",
                        "message": "질문을 해석했습니다.",
                        "status": "completed",
                    }
                ],
                "preprocess_result": None,
            },
        }

    async def resume_run_stream(
        self,
        *,
        session_id: int,
        run_id: str,
        decision: str,
        stage: str,
        instruction: str | None = None,
    ):
        yield {"event": "session", "data": {"session_id": session_id, "run_id": run_id}}
        yield {
            "event": "done",
            "data": {
                "answer": "재개 완료",
                "session_id": session_id,
                "run_id": run_id,
                "thought_steps": [],
                "preprocess_result": None,
            },
        }

    def get_pending_approval(self, *, session_id: int, run_id: str):
        if session_id == 1 and run_id == "run-approval":
            return self.pending
        return None

    def get_history(self, session_id: int):
        raise NotImplementedError

    def delete_session(self, session_id: int):
        raise NotImplementedError


class ChatStreamContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_service = FakeChatService()
        app.dependency_overrides[get_chat_service] = lambda: self.fake_service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.client.close()

    def test_stream_happy_path_emits_session_thought_chunk_done(self):
        response = self.client.post(
            "/chats/stream",
            json={"question": "happy", "session_id": None, "model_id": None, "source_id": None},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        events = _parse_sse_events(response.text)
        self.assertEqual([name for name, _ in events], ["session", "thought", "chunk", "done"])
        self.assertEqual(events[0][1]["session_id"], 1)
        self.assertEqual(events[0][1]["run_id"], "run-1")
        self.assertEqual(events[3][1]["answer"], "최종 응답")

    def test_stream_approval_path_emits_session_then_approval_required(self):
        response = self.client.post(
            "/chats/stream",
            json={"question": "approval", "session_id": None, "model_id": None, "source_id": "source-1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        events = _parse_sse_events(response.text)
        self.assertEqual([name for name, _ in events], ["session", "approval_required"])
        payload = events[1][1]
        self.assertEqual(payload["session_id"], 1)
        self.assertEqual(payload["run_id"], "run-approval")
        self.assertIn("pending_approval", payload)
        self.assertIn("thought_steps", payload)

    def test_resume_stream_emits_session_then_done(self):
        response = self.client.post(
            "/chats/1/runs/run-approval/resume",
            json={"decision": "approve", "stage": "preprocess", "instruction": ""},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        events = _parse_sse_events(response.text)
        self.assertEqual([name for name, _ in events], ["session", "done"])
        self.assertEqual(events[0][1]["session_id"], 1)
        self.assertEqual(events[1][1]["answer"], "재개 완료")

    def test_pending_approval_lookup_shape_is_preserved(self):
        response = self.client.get("/chats/1/runs/run-approval/pending-approval")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["session_id"], 1)
        self.assertEqual(body["run_id"], "run-approval")
        self.assertEqual(body["pending_approval"]["stage"], "preprocess")


if __name__ == "__main__":
    unittest.main()
