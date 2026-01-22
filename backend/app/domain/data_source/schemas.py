from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class DatasetRead(BaseModel):
    """
    DB에 저장된 Dataset 한 건을 읽어올 때 사용하는 스키마.
    SELECT 결과를 반환할 때 사용.
    models.Dataset과 필드 이름/타입을 맞춤.
    """
    id: int
    source_id: str
    workspace_id: Optional[str] = None
    
    filename: str
    storage_path: str
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    filesize: Optional[int] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    uploaded_at: datetime

    class Config: # SQLAlchemy 모델 객체를 그대로 응답으로 리턴할 수 있게 해주는 설정
        orm_mode = True


class DatasetUploadRequest(BaseModel):
    """
    파일 업로드 요청 시 함께 전달되는 옵션 정보 스키마(프론트 -> 벡엔드로 보내는 업로드 옵션 정보)
    실제 파일 내용은 FastAPI의 UploadFile로 받고,
    이 클래스는 업로드 옵션(메타 정보)만 JSON으로 받음.
    """
    encoding: Optional[str] = None
    delimiter: Optional[str] = None


class DatasetUploadResponse(BaseModel):
    """
    파일 업로드 성공 시, 프론트에 돌려주는 응답 스키마.
    - 업로드된 데이터셋의 기본 메타 정보
    """
    id: int
    source_id: str
    workspace_id: Optional[str] = None
    
    filename: str
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    filesize: Optional[int] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    uploaded_at: datetime
    
    class Config:
        orm_mode = True
    
    
class DatasetListItem(BaseModel):
    """
    데이터 소스 목록 조회용 한 줄 요약 아이템.
    리스트 화면에서 필요한 최소 정보만 노출.
    """
    id: int
    source_id: str
    workspace_id: Optional[str] = None

    filename: str
    filesize: Optional[int] = None
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    uploaded_at: datetime

    class Config:
        orm_mode = True


class DatasetListResponse(BaseModel):
    """
    데이터 소스 목록 응답
    - total: 워크스페이스(또는 전체) 기준 전체 개수
    - items: 현재 페이지의 데이터 소스 리스트
    """
    total: int
    items: List[DatasetListItem]

class DeletedFileInfo(BaseModel):
    """
    삭제된 파일 정보
    """
    source_id: str
    filename: str
    storage_path: str

class DatasetDeleteResponse(BaseModel):
    """
    데이터 소스 삭제 응답 스키마
    - 성공 시: 204 No Content (response_model 없이 처리)
    - 삭제된 파일 정보는 내부적으로만 사용
    """
    success: bool
    deleted_file: Optional[DeletedFileInfo] = None

class DatasetMetadataResponse(BaseModel):
    """
    데이터 소스 메타데이터 조회 응답
    """
    source_id: str
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    line_ending: Optional[str] = None
    quotechar: Optional[str] = None
    escapechar: Optional[str] = None
    has_header: Optional[bool] = None
    parse_status: Optional[str] = None  # 'success', 'tentative', 'failed'


class DatasetMetadataUpdateRequest(BaseModel):
    """
    데이터 소스 메타데이터 수정 요청
    """
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    has_header: Optional[bool] = None


class DatasetMetadataUpdateResponse(BaseModel):
    """
    데이터 소스 메타데이터 수정 응답
    """
    source_id: str
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    has_header: Optional[bool] = None
    updated: bool = True

class DatasetVersionOut(BaseModel):
    """
    전처리 후 생성된 데이터 버전의 메타 정보 응답
    """
    id: int
    dataset_id: int
    base_version_id: Optional[int] = None
    version_no: int
    file_path: str
    row_count: Optional[int] = None
    col_count: Optional[int] = None
    operations_json: str
    created_by: Optional[str] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True


class DatasetVersionsResponse(BaseModel):
    """
    모든 전처리 버전 목록 응답
    """
    dataset_id: int
    versions: List[DatasetVersionOut]
    
class DatasetSampleResponse(BaseModel):
    """
    데이터셋 샘플 데이터 응답 스키마
    """
    source_id: str
    columns: List[str]  # 열 이름 리스트
    rows: List[Dict[str, Any]]  # 상위 5개 데이터 행
    

class ChartColumns(BaseModel):
    """수동 시각화 요청 컬럼 설정"""
    x: str
    y: str
    color: Optional[str] = None
    group: Optional[str] = None


class ManualVizRequest(BaseModel):
    """수동 시각화 요청 객체"""
    source_id: str
    chart_type: str = Field(..., pattern="^(bar|line|pie|scatter|heatmap)$")
    columns: ChartColumns
    limit: Optional[int] = 500


class ManualVizResponse(BaseModel):
    """수동 시각화 응답 객체"""
    chart_type: str
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]
