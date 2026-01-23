from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

PreprocessOpType = Literal[
    "drop_missing",      # 결측치 행 제거
    "impute",            # 결측치 대체
    "drop_columns",      # 컬럼 삭제
    "rename_columns",    # 컬럼명 변경
    "scale",             # 표준화 / 정규화
    "derived_column",    # 파생 변수 생성
]


class PreprocessOperation(BaseModel):
    """
    단일 전처리 작업 정의
    """
    op: PreprocessOpType
    params: Dict[str, Any] = Field(default_factory=dict)

# --- preview ---
class PreprocessPreviewRequest(BaseModel):
    """
    전처리 UI 진입용 미리보기 요청
    """
    dataset_id: int
    version_id: Optional[int] = None


class ColumnPreview(BaseModel):
    """
    컬럼 미리보기 정보
    """
    name: str
    dtype: str
    missing: int


class PreprocessPreviewResponse(BaseModel):
    """
    전처리 UI 표시용 데이터
    """
    dataset_id: int
    version_id: Optional[int]
    columns: List[ColumnPreview]
    sample_rows: List[Dict[str, Any]]

# --- apply ---
class PreprocessApplyRequest(BaseModel):
    """
    전처리 적용 요청
    """
    dataset_id: int
    base_version_id: Optional[int] = None
    operations: List[PreprocessOperation]
    created_by: Optional[str] = None
    note: Optional[str] = None


class PreprocessApplyResponse(BaseModel):
    """
    전처리 적용 결과
    """
    dataset_id: int
    base_version_id: Optional[int]
    new_version_id: int
    version_no: int
    row_count: int
    col_count: int
