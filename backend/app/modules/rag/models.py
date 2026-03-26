from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from ...core.db import Base


class RagSource(Base):
    __tablename__ = "rag_sources"

    source_id = Column(
        String(36),
        ForeignKey("datasets.source_id", ondelete="CASCADE"),
        primary_key=True,
    )
    checksum = Column(String(64), nullable=False)
    embedding_model = Column(String(128), nullable=False)
    embedding_dim = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False)
    indexed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(
        String(36),
        ForeignKey("rag_sources.source_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    faiss_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RagContext(Base):
    __tablename__ = "rag_context"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_id = Column(
        String(36),
        ForeignKey("rag_sources.source_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("rag_chunks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GuidelineRagSource(Base):
    """
    지침서 문서의 RAG 인덱싱 메타데이터 관리 테이블.
    """

    __tablename__ = "guideline_rag_sources"

    source_id = Column(
        String(36),
        ForeignKey("guidelines.source_id", ondelete="CASCADE"),
        primary_key=True,
    )
    checksum = Column(String(64), nullable=False)
    embedding_model = Column(String(128), nullable=False)
    embedding_dim = Column(Integer, nullable=False)
    chunk_count = Column(Integer, nullable=False)
    indexed_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GuidelineRagChunk(Base):
    """
    지침서에서 분할된 텍스트 청크 저장 테이블.
    """

    __tablename__ = "guideline_rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(
        String(36),
        ForeignKey("guideline_rag_sources.source_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    faiss_id = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GuidelineRagContext(Base):
    """
    채팅 세션과 참조한 지침서 청크 간의 연결 테이블.
    """

    __tablename__ = "guideline_rag_context"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_id = Column(
        String(36),
        ForeignKey("guideline_rag_sources.source_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id = Column(
        Integer,
        ForeignKey("guideline_rag_chunks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
