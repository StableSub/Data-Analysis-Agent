from typing import Optional

from .repository import ChatRepository
from .schemas import ChatHistoryResponse, ChatResponse
from ...ai.orchestrator.chat_flow import ChatFlowOrchestrator


class ChatService:
    """Coordinates chat domain logic and AI orchestration."""

    def __init__(self, repository: ChatRepository, orchestrator: ChatFlowOrchestrator) -> None:
        self.repository = repository
        self.orchestrator = orchestrator

    def ask(self, *, question: str, session_id: Optional[int] = None) -> ChatResponse:
        session = None
        if session_id:
            session = self.repository.get_session(session_id)
        if session is None:
            session = self.repository.create_session(title=question[:60])

        answer = self.orchestrator.generate_answer(session_id=session.id, question=question)
        return ChatResponse(answer=answer, session_id=session.id)

    def get_history(self, session_id: int) -> Optional[ChatHistoryResponse]:
        session = self.repository.get_session(session_id)
        if not session:
            return None
        messages = self.repository.get_history(session_id)
        return ChatHistoryResponse(session_id=session_id, messages=messages)
