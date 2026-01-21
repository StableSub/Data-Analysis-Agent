from sqlalchemy import Column, DateTime, Integer, JSON, String, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ...core.db import Base
import uuid

class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True) # DB 내부 ID
    source_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))  # 외부 노출용 고유 데이터 소스 ID
    workspace_id = Column(String(64), nullable=True, index=True)    # 데이터가 속한 workspace ID
        
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False)  # 서버 또는 스토리지에 저장된 파일 경로
    encoding = Column(String(64), nullable=True)    # 인코딩 정보: 'utf-8'
    delimiter = Column(String(8), nullable=True)    # 구분자 정보: ',', '\t' 등
    filesize = Column(Integer, nullable=True)       # 파일 크기 (bytes)
    extra_metadata = Column(JSON, nullable=True)    # 추가 메타데이터 (예: 행/열 수)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now()) # 업로드 시각(default: 현재 시각)

    line_ending = Column(String(8), nullable=True)      # 줄바꿈 문자: '\n', '\r\n', '\r'
    quotechar = Column(String(4), nullable=True)        # 따옴표 문자: '"'
    escapechar = Column(String(4), nullable=True)       # 이스케이프 문자
    has_header = Column(Boolean, nullable=True, default=True)  # 헤더 존재 여부
    parse_status = Column(String(16), nullable=True)    # 파싱 상태: 'success', 'tentative', 'failed'

class SessionSource(Base):
    """
    세션과 데이터 소스 간의 관계를 저장하는 테이블
    어떤 세션에서 어떤 데이터셋을 사용하고 있는지 추적
    """
    __tablename__ = "session_sources"
    
    id = Column(Integer, primary_key=True, index=True)  # 관계 테이블 ID
    session_id = Column(String(64), nullable=False, index=True)  # 세션 ID
    
    # ForeignKey 추가 - Dataset 테이블의 source_id 참조
    source_id = Column(
        String(36),
        ForeignKey('datasets.source_id', ondelete='CASCADE'),  # Dataset 삭제 시 함께 삭제
        nullable=False,
        index=True
    )
    
    # 세션에 데이터 소스가 추가된 시각
    added_at = Column(DateTime(timezone=True), server_default=func.now())

class DatasetVersion(Base):
    """
    데이터셋 전처리 결과 버전 정보를 저장
    """
    __tablename__ = "dataset_versions"

    id = Column(Integer, primary_key=True, index=True)

    # 원본 ID
    dataset_id = Column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 이전 버전 ID 
    base_version_id = Column(
        Integer,
        ForeignKey("dataset_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    version_no = Column(Integer, nullable=False, default=1)

    # 전처리 후 저장된 파일 경로
    file_path = Column(String(1024), nullable=False)

    row_count = Column(Integer, nullable=True)
    col_count = Column(Integer, nullable=True)

    # 적용된 전처리 작업
    operations_json = Column(Text, nullable=False, default="[]")

    created_by = Column(String(255), nullable=True)
    note = Column(String(1024), nullable=True)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    dataset = relationship("Dataset", backref="versions")
    base_version = relationship("DatasetVersion", remote_side=[id], uselist=False)
