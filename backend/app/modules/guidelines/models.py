import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from ...core.db import Base


class Guideline(Base):
    """업로드된 회사 지침서 메타데이터를 저장하는 ORM 모델."""

    __tablename__ = "guidelines"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    guideline_id = Column(
        String(64),
        unique=True,
        index=True,
        default=lambda: f"guide_{uuid.uuid4().hex[:12]}",
    )
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    filesize = Column(Integer, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

