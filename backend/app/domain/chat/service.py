from typing import Optional

from .repository import ChatRepository
from .schemas import ChatHistoryResponse, ChatResponse
from ...ai.orchestrator.chat_flow import ChatFlowOrchestrator
from .models import ChatSession, ChatMessage


class ChatService:
    """채팅 세션 생성, 메시지 저장/조회, 간단한 응답 생성을 담당합니다."""

    def __init__(self, repository: ChatRepository, orchestrator: ChatFlowOrchestrator) -> None:
        self.repository = repository
        self.orchestrator = orchestrator

    def ask(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        context: Optional[str] = None,
    ) -> ChatResponse:
        """질문을 저장하고 간단한 응답을 생성합니다."""
        session = self.repository.get_session(session_id) if session_id else None
        if session is None:
            session = self.repository.create_session(title=question[:60])

        history = self.repository.get_history(session.id)
        answer = self.orchestrator.generate_answer(
            session_id=session.id,
            question=question,
            history=history,
            context=context,
        )

        self.repository.append_message(session, "user", question)
        self.repository.append_message(session, "assistant", answer)
        return ChatResponse(answer=answer, session_id=session.id)

    def get_history(self, session_id: int) -> Optional[ChatHistoryResponse]:
        """세션의 전체 히스토리를 반환합니다."""
        session = self.repository.get_session(session_id)
        if not session:
            return None
        messages = self.repository.get_history(session_id)
        return ChatHistoryResponse(session_id=session_id, messages=messages)
