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
