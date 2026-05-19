from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ChartSeriesPayload(BaseModel):
    name: str | None = None
    y: List[Any] | None = None


class ChartDataPayload(BaseModel):
    chart_type: str | None = None
    x_key: str | None = None
    y_key: str | None = None
    x: List[Any] | None = None
    series: List[ChartSeriesPayload] = Field(default_factory=list)
    caption: str | None = None


class VisualizationArtifactPayload(BaseModel):
    mime_type: str = "image/png"
    image_base64: str | None = None
    code: str | None = None


class VisualizationResultPayload(BaseModel):
    status: str
    source_id: str = ""
    summary: str = ""
    chart: ChartDataPayload | None = None
    chart_data: ChartDataPayload | None = None
    charts: List[ChartDataPayload] | None = None
    artifact: VisualizationArtifactPayload | None = None
    fallback_table: List[Dict[str, Any]] | None = None


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
