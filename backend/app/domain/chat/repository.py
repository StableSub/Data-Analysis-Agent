from typing import List, Optional

from sqlalchemy.orm import Session

from .models import ChatMessage, ChatSession


class ChatRepository:
    """Database access for chat sessions and messages."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_session(self, session_id: int) -> Optional[ChatSession]:
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def create_session(self, title: Optional[str] = None) -> ChatSession:
        session = ChatSession(title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def append_message(self, session: ChatSession, role: str, content: str) -> ChatMessage:
        message = ChatMessage(session=session, role=role, content=content)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_history(self, session_id: int) -> List[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )

    def delete_session(self, session_id: int) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        self.db.delete(session)
        self.db.commit()
        return True
