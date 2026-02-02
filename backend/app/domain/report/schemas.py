from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    """리포트 생성 요청 DTO."""
    session_id: int = Field(..., description="Chat session id to attach the report to.")
    analysis_results: List[Dict[str, Any]] = Field(default_factory=list)
    visualizations: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[Any] = Field(default_factory=list)


class ReportCreateResponse(BaseModel):
    """리포트 생성 응답 DTO."""
    report_id: str
    session_id: int
    version: int
    summary_text: str
    created_at: datetime

    class Config:
        orm_mode = True


class ReportReadResponse(BaseModel):
    """리포트 단건 조회 응답 DTO."""
    report_id: str
    session_id: int
    version: int
    summary_text: str
    payload_json: Optional[Dict[str, Any]] = None
    llm_model: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class ReportListItem(BaseModel):
    """리포트 목록 아이템 DTO."""
    report_id: str
    session_id: int
    version: int
    created_at: datetime

    class Config:
        orm_mode = True


class ReportListResponse(BaseModel):
    """세션별 리포트 목록 응답 DTO."""
    session_id: int
    items: List[ReportListItem]


class ReportExportResponse(BaseModel):
    """내보내기 결과 응답 DTO."""
    report_id: str
    format: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True
