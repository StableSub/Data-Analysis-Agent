from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    session_id: int = Field(..., description="연결할 chat session id")
    analysis_results: List[Dict[str, Any]] = Field(default_factory=list)
    visualizations: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[Any] = Field(default_factory=list)


class ReportBase(BaseModel):
    report_id: str
    session_id: int
    summary_text: str


class ReportListResponse(BaseModel):
    session_id: int
    items: List[ReportBase]
