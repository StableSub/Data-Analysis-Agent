from typing import Any, AsyncIterator, Dict, Optional

from .run_service import ChatRunService
from .schemas import ChatHistoryResponse, ChatResponse, PendingApprovalResponse
from .session_service import ChatSessionService


class ChatService:
    """채팅 진입 계층."""

    def __init__(
        self,
        *,
        session_service: ChatSessionService,
        run_service: ChatRunService,
    ) -> None:
        self.session_service = session_service
        self.run_service = run_service

    async def ask(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        model_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> ChatResponse:
        done_payload: Dict[str, Any] | None = None
        approval_payload: Dict[str, Any] | None = None
        async for event in self.ask_stream(
            question=question,
            session_id=session_id,
            model_id=model_id,
            source_id=source_id,
        ):
            if event.get("event") == "done":
                payload = event.get("data")
                if isinstance(payload, dict):
                    done_payload = payload
            elif event.get("event") == "approval_required":
                payload = event.get("data")
                if isinstance(payload, dict):
                    approval_payload = payload

        if approval_payload is not None:
            session_id_value = approval_payload.get("session_id")
            run_id = approval_payload.get("run_id")
            thought_steps = approval_payload.get("thought_steps")
            pending_approval = approval_payload.get("pending_approval")
            if not isinstance(session_id_value, int):
                raise RuntimeError("chat stream finished without session id")
            return ChatResponse(
                answer="",
                session_id=session_id_value,
                run_id=run_id if isinstance(run_id, str) else None,
                thought_steps=thought_steps if isinstance(thought_steps, list) else [],
                pending_approval=pending_approval if isinstance(pending_approval, dict) else None,
            )

        if done_payload is None:
            raise RuntimeError("chat stream finished without done event")

        answer = done_payload.get("answer")
        session_id_value = done_payload.get("session_id")
        thought_steps = done_payload.get("thought_steps")
        if not isinstance(session_id_value, int):
            raise RuntimeError("chat stream finished without session id")
        return ChatResponse(
            answer=str(answer) if isinstance(answer, str) else "",
            session_id=session_id_value,
            run_id=done_payload.get("run_id") if isinstance(done_payload.get("run_id"), str) else None,
            thought_steps=thought_steps if isinstance(thought_steps, list) else [],
        )

    async def ask_stream(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        model_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        async for event in self.run_service.ask_stream(
            question=question,
            session_id=session_id,
            model_id=model_id,
            source_id=source_id,
        ):
            yield event

    async def resume_run_stream(
        self,
        *,
        session_id: int,
        run_id: str,
        decision: str,
        stage: str,
        instruction: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        async for event in self.run_service.resume_run_stream(
            session_id=session_id,
            run_id=run_id,
            decision=decision,
            stage=stage,
            instruction=instruction,
        ):
            yield event

    def get_pending_approval(
        self,
        *,
        session_id: int,
        run_id: str,
    ) -> PendingApprovalResponse | None:
        return self.run_service.get_pending_approval(session_id=session_id, run_id=run_id)

    def get_history(self, session_id: int) -> Optional[ChatHistoryResponse]:
        return self.session_service.get_history(session_id)

    def delete_session(self, session_id: int) -> bool:
        return self.session_service.delete_session(session_id)
