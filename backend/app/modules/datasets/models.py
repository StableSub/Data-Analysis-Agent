import uuid
from typing import Final

from sqlalchemy import Column, Integer, String

from ...core.db import Base

DATASET_SOURCE_ID_MAX_LENGTH: Final = 255
DATASET_FILENAME_MAX_LENGTH: Final = 255


class Dataset(Base):
    """업로드된 데이터 파일의 최소 메타데이터를 저장하는 ORM 모델."""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(
        String(DATASET_SOURCE_ID_MAX_LENGTH),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    filename = Column(String(DATASET_FILENAME_MAX_LENGTH), nullable=False)
    storage_path = Column(String(512), nullable=False)
    filesize = Column(Integer, nullable=True)
