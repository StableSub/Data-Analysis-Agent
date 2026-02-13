from typing import Any, Dict, List
from pydantic import BaseModel, Field

class DatasetBase(BaseModel):
    """데이터셋 기본 응답 형태(단건/업로드/목록 아이템 공용)."""

    id: int
    source_id: str
    filename: str
    storage_path: str
    filesize: int | None = None

    class Config:
        orm_mode = True

class DatasetListResponse(BaseModel):
    """데이터셋 목록 응답 형태."""

    total: int
    items: List[DatasetBase]

class DatasetSampleResponse(BaseModel):
    """데이터셋 샘플 조회 응답 형태."""

    source_id: str
    columns: List[str]
    rows: List[Dict[str, Any]]

class ChartColumns(BaseModel):
    """수동 시각화에 사용할 컬럼 매핑 정의."""

    x: str
    y: str
    color: str | None = None
    group: str | None = None

class ManualVizRequest(BaseModel):
    """수동 시각화 데이터 생성 요청 형태."""

    source_id: str
    chart_type: str = Field(..., pattern=r"^(bar|line|pie|scatter|heatmap)$")
    columns: ChartColumns
    limit: int | None = 500

class ManualVizResponse(BaseModel):
    """수동 시각화 데이터 생성 응답 형태."""

    chart_type: str
    data: List[Dict[str, Any]]
