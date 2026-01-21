from typing import Optional, List
from pydantic import BaseModel, Field

# CSV 내보내기 
class CsvExportParams(BaseModel):
    result_id: Optional[str] = Field(None, description="Analysis result ID")
    view_token: Optional[str] = Field(None, description="Current view snapshot token (used when result_id is not provided)")
    
    # 선택 파라미터 (export as displayed)
    columns: Optional[List[str]] = Field(None, description="List of specific columns to export")
    limit: Optional[int] = Field(None, description="Maximum number of rows to export")
    include_header: bool = Field(True, description="Whether to include the header row")

# PNG 내보내기
class ChartExportParams(BaseModel):
    chart_id: str = Field(..., description="Chart ID")
    
    # 선택 파라미터
    scale: int = Field(2, ge=1, le=5, description="Image resolution scale (default: 2)")
    bg: str = Field("transparent", description="Background color (default: transparent, e.g. #ffffff)")
