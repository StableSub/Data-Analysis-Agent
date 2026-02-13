from typing import Any, Dict, List

from pydantic import BaseModel, Field

class ReportCreateRequest(BaseModel):
    """리포트 생성 요청 DTO."""

    session_id: int = Field(..., description="연결할 chat session id")
    analysis_results: List[Dict[str, Any]] = Field(default_factory=list)
    visualizations: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[Any] = Field(default_factory=list)

class ReportBase(BaseModel):
    """리포트 공통 응답 DTO."""

    report_id: str
    session_id: int
    summary_text: str

class ReportListResponse(BaseModel):
    """세션별 리포트 목록 응답 DTO."""

    session_id: int
    items: List[ReportBase]
