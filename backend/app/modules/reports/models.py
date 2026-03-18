import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from ...core.db import Base


class Report(Base):
    """리포트 본문을 저장하는 최소 ORM 모델."""

    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    summary_text = Column(Text, nullable=False)
