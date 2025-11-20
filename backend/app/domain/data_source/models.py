from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func

from ...core.db import Base


class Dataset(Base):
    """Persisted dataset metadata."""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    encoding = Column(String(64), nullable=True)
    delimiter = Column(String(8), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
