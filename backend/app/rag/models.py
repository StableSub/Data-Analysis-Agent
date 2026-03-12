from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from ..core.db import Base


class RagSource(Base):
    """
    RAG 인덱싱된 문서의 메타데이터 관리 테이블.
    원본 파일의 임베딩 설정 및 인덱싱 상태를 저장.
    """

    __tablename__ = "rag_sources"

    source_id = Column(
        String(36),
        ForeignKey("datasets.source_id", ondelete="CASCADE"),
        primary_key=True,
    )
    checksum = Column(
        String(64), nullable=False
    )  # 중복 처리 방지를 위한 파일 내용 해시값
    embedding_model = Column(String(128), nullable=False)  # 사용된 임베딩 모델명
    embedding_dim = Column(Integer, nullable=False)  # 벡터 차원 수
    chunk_count = Column(Integer, nullable=False)  # 분할된 총 청크 개수
    indexed_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RagChunk(Base):
    """
    분할된 텍스트 청크 데이터 저장 테이블.
    벡터 DB 검색 후 원문 내용을 조회하기 위해 사용.
    """

    __tablename__ = "rag_chunks"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(
        String(36),
        ForeignKey("rag_sources.source_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_id = Column(Integer, nullable=False)  # 문서 내 청크 순번
    content = Column(Text, nullable=False)  # 청크 원문 텍스트
    faiss_id = Column(Integer, nullable=False)  # FAISS 벡터 인덱스 내부 ID와의 매핑값
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RagContext(Base):
    """
    채팅 세션과 참조 문서 간의 연결 테이블.
    특정 대화에서 어떤 문서의 어떤 청크를 참고했는지 추적.
    """

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
