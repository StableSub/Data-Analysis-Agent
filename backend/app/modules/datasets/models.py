import uuid

from sqlalchemy import Column, Integer, String

from ...core.db import Base


class Dataset(Base):
    """업로드된 데이터 파일의 최소 메타데이터를 저장하는 ORM 모델."""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)
    filesize = Column(Integer, nullable=True)
