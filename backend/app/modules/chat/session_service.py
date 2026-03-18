from typing import Optional

from .models import ChatSession
from .repository import ChatRepository
from .schemas import ChatHistoryResponse


class ChatSessionService:
    """세션/메시지 영속화만 담당한다."""

    def __init__(self, repository: ChatRepository) -> None:
        self.repository = repository

    def get_session(self, session_id: int) -> Optional[ChatSession]:
        return self.repository.get_session(session_id)

    def get_or_create_session(self, *, session_id: int | None, title: str) -> ChatSession:
        session = self.repository.get_session(session_id) if session_id else None
        if session is None:
            session = self.repository.create_session(title=title[:60])
        return session

    def append_message(self, *, session: ChatSession, role: str, content: str) -> None:
        self.repository.append_message(session, role, content)

    def get_history(self, session_id: int) -> Optional[ChatHistoryResponse]:
        session = self.repository.get_session(session_id)
        if not session:
            return None
        messages = self.repository.get_history(session_id)
        return ChatHistoryResponse(session_id=session_id, messages=messages)

    def delete_session(self, session_id: int) -> bool:
        return self.repository.delete_session(session_id)
