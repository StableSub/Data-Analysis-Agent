import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from ...core.db import Base


class Report(Base):
    """리포트 메타/본문을 저장하는 테이블."""
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("session_id", "version", name="uq_reports_session_version"),
    )

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    # 세션 기준 버전 관리
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)

    # LLM 요약 결과와 입력 payload
    summary_text = Column(Text, nullable=False)
    payload_json = Column(JSON, nullable=True)
    llm_model = Column(String(64), nullable=True)
    prompt_version = Column(String(32), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ReportExport(Base):
    """내보내기 결과(파일/상태)를 저장하는 테이블."""
    __tablename__ = "report_exports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(
        String(36),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # txt | md | pdf
    format = Column(String(8), nullable=False)
    status = Column(String(16), nullable=False, default="success")
    file_path = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
