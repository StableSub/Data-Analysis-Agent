import uuid

from sqlalchemy import Column, ForeignKey, Integer, String

from ...core.db import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    filesize = Column(Integer, nullable=True)


class SessionSource(Base):
    __tablename__ = "session_sources"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    source_id = Column(
        String(36),
        ForeignKey("datasets.source_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
