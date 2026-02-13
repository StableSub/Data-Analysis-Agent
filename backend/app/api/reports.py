from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..ai.agents.client import AgentClient
from ..core.db import get_db
from ..dependencies import get_agent
from ..domain.report.schemas import ReportBase, ReportCreateRequest, ReportListResponse
from ..domain.report.service import ReportService

router = APIRouter(prefix="/report", tags=["report"])


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """ReportService 의존성 주입."""
    return ReportService(db=db)


@router.post("/", response_model=ReportBase)
def create_report(
    request: ReportCreateRequest,
    service: ReportService = Depends(get_report_service),
    agent: AgentClient = Depends(get_agent),
):
    """리포트를 생성한다."""
    report = service.create_report(
        session_id=request.session_id,
        analysis_results=request.analysis_results,
        visualizations=request.visualizations,
        insights=request.insights,
        agent=agent,
    )
    return ReportBase(
        report_id=report.id,
        session_id=report.session_id,
        summary_text=report.summary_text,
    )


@router.get("/", response_model=ReportListResponse)
def list_reports(
    session_id: int = Query(..., description="Session ID"),
    service: ReportService = Depends(get_report_service),
):
    """세션별 리포트 목록 조회."""
    items = service.list_reports(session_id)
    return ReportListResponse(
        session_id=session_id,
        items=[
            {
                "report_id": item.id,
                "session_id": item.session_id,
                "summary_text": item.summary_text,
            }
            for item in items
        ],
    )


@router.get("/{report_id}", response_model=ReportBase)
def get_report(
    report_id: str,
    service: ReportService = Depends(get_report_service),
):
    """리포트 단건 조회."""
    report = service.get_report(report_id)
    return ReportBase(
        report_id=report.id,
        session_id=report.session_id,
        summary_text=report.summary_text,
    )
