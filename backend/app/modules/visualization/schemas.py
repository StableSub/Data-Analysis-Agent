from typing import Any, Dict, List

from pydantic import BaseModel, Field


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


class VisualizationFromAnalysisRequest(BaseModel):
    analysis_result_id: str


class VisualizationFromAnalysisResponse(BaseModel):
    status: str
    source_id: str
    summary: str
    chart: Dict[str, Any] | None = None
    chart_data: Dict[str, Any] | None = None
    fallback_table: List[Dict[str, Any]] | None = None
