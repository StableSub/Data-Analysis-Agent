from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.sql import func
from ...core.db import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)  # 서버 또는 스토리지에 저장된 파일 경로
    encoding = Column(String(64), nullable=True)    # 인코딩 정보: 'utf-8'
    delimiter = Column(String(8), nullable=True)    # 구분자 정보: ',', '\t' 등
    filesize = Column(Integer, nullable=True)       # 파일 크기 (bytes)
    extra_metadata = Column(JSON, nullable=True)    # 추가 메타데이터 (예: 행/열 수)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now()) # 업로드 시각(default: 현재 시각)
    