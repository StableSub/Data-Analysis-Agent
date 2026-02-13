from typing import Any, Dict, List
from pydantic import BaseModel, Field

class DatasetBase(BaseModel):
    id: int
    source_id: str
    filename: str
    storage_path: str
    filesize: int | None = None

    class Config:
        orm_mode = True

class DatasetListResponse(BaseModel):
    total: int
    items: List[DatasetBase]

class DatasetSampleResponse(BaseModel):
    source_id: str
    columns: List[str]
    rows: List[Dict[str, Any]]

class ChartColumns(BaseModel):
    x: str
    y: str
    color: str | None = None
    group: str | None = None

class ManualVizRequest(BaseModel):
    source_id: str
    chart_type: str = Field(..., pattern=r"^(bar|line|pie|scatter|heatmap)$")
    columns: ChartColumns
    limit: int | None = 500

class ManualVizResponse(BaseModel):
    chart_type: str
    data: List[Dict[str, Any]]
