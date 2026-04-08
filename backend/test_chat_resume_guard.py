from __future__ import annotations

import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from backend.app.modules.chat.router import resume_chat_run
from backend.app.modules.chat.schemas import PendingApproval, PendingApprovalResponse, ResumeRunRequest
from backend.app.modules.chat.service import ChatService


class _FakeResumeGuardChatService:
    def __init__(
        self,
        *,
        has_session: bool = True,
        pending_session_id: int | None = 7,
    ) -> None:
        self._has_session = has_session
        self._pending_session_id = pending_session_id
        self.resume_calls = 0

    def has_session(self, session_id: int) -> bool:
        return self._has_session

    async def get_pending_approval(self, *, run_id: str) -> PendingApprovalResponse | None:
        if self._pending_session_id is None:
            return None
        return PendingApprovalResponse(
            session_id=self._pending_session_id,
            run_id=run_id,
            pending_approval=PendingApproval(
                stage="preprocess",
                kind="plan_review",
                title="Review preprocess plan",
                summary="Confirm the generated preprocessing plan.",
                source_id="source-1",
            ),
        )

    def resume_run_stream(self, **kwargs):
        self.resume_calls += 1

        async def iterator():
            yield {
                "event": "done",
                "data": {
                    "session_id": kwargs["session_id"],
                    "run_id": kwargs["run_id"],
                    "trace_id": "trace-resume",
                    "answer": "resume ok",
                },
            }

        return iterator()


class _FakeChatRepository:
    def __init__(self, session_id: int = 7) -> None:
        self.session = SimpleNamespace(id=session_id)
        self.appended_messages: list[tuple[int, str, str]] = []

    def get_session(self, session_id: int):
        if session_id == self.session.id:
            return self.session
        return None

    def append_message(self, session, role: str, content: str):
        self.appended_messages.append((session.id, role, content))
        return SimpleNamespace(session_id=session.id, role=role, content=content)


class _FakeResumeAgent:
    def __init__(self) -> None:
        self.resume_calls: list[dict[str, object]] = []

    def astream_with_trace(self, **kwargs):
        self.resume_calls.append(kwargs)

        async def iterator():
            yield {
                "type": "done",
                "answer": "resume completed",
                "thought_steps": [],
            }

        return iterator()


async def _collect_stream(response: StreamingResponse) -> str:
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunks.append(chunk.decode("utf-8"))
        else:
            chunks.append(chunk)
    return "".join(chunks)


class ResumeGuardRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_resume_route_streams_when_session_matches_pending_approval(self) -> None:
        chat_service = _FakeResumeGuardChatService(has_session=True, pending_session_id=7)

        response = await resume_chat_run(
            session_id=7,
            run_id="run-7",
            request=ResumeRunRequest(decision="approve", stage="preprocess"),
            chat_service=chat_service,
        )

        self.assertIsInstance(response, StreamingResponse)
        body = await _collect_stream(response)
        self.assertIn("event: done", body)
        self.assertIn("resume ok", body)
        self.assertEqual(chat_service.resume_calls, 1)

    async def test_resume_route_rejects_missing_session(self) -> None:
        chat_service = _FakeResumeGuardChatService(has_session=False, pending_session_id=7)

        with self.assertRaises(HTTPException) as context:
            await resume_chat_run(
                session_id=7,
                run_id="run-7",
                request=ResumeRunRequest(decision="approve", stage="preprocess"),
                chat_service=chat_service,
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(chat_service.resume_calls, 0)

    async def test_resume_route_rejects_missing_pending_approval(self) -> None:
        chat_service = _FakeResumeGuardChatService(has_session=True, pending_session_id=None)

        with self.assertRaises(HTTPException) as context:
            await resume_chat_run(
                session_id=7,
                run_id="run-7",
                request=ResumeRunRequest(decision="approve", stage="preprocess"),
                chat_service=chat_service,
            )

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(chat_service.resume_calls, 0)

    async def test_resume_route_rejects_session_run_mismatch(self) -> None:
        chat_service = _FakeResumeGuardChatService(has_session=True, pending_session_id=9)

        with self.assertRaises(HTTPException) as context:
            await resume_chat_run(
                session_id=7,
                run_id="run-9",
                request=ResumeRunRequest(decision="approve", stage="preprocess"),
                chat_service=chat_service,
            )

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(chat_service.resume_calls, 0)


class ChatServiceResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_resume_run_stream_appends_final_message_to_matching_session(self) -> None:
        repository = _FakeChatRepository(session_id=7)
        agent = _FakeResumeAgent()
        service = ChatService(
            agent=agent,
            repository=repository,
            dataset_repository=SimpleNamespace(),
        )

        events = []
        async for event in service.resume_run_stream(
            session_id=7,
            run_id="run-7",
            decision="approve",
            stage="preprocess",
        ):
            events.append(event)

        self.assertEqual(events[0]["event"], "session")
        self.assertEqual(events[-1]["event"], "done")
        self.assertEqual(repository.appended_messages, [(7, "assistant", "resume completed")])
        self.assertEqual(len(agent.resume_calls), 1)
        self.assertEqual(agent.resume_calls[0]["session_id"], "7")
        self.assertEqual(agent.resume_calls[0]["run_id"], "run-7")


if __name__ == "__main__":
    unittest.main()
