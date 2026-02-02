from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..dependencies import get_llm_client
from ..ai.llm.client import LLMClient
from ..domain.report.schemas import (
    ReportCreateRequest,
    ReportCreateResponse,
    ReportListResponse,
    ReportReadResponse,
)
from ..domain.report.service import ReportService

router = APIRouter(prefix="/report", tags=["report"])


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """ReportService 의존성 주입."""
    storage_dir = Path("storage") / "reports"
    return ReportService(db=db, storage_dir=storage_dir)


@router.get("/export")
def export_report(
    report_id: str = Query(..., description="Report ID"),
    format: str = Query("pdf", description="txt | md | pdf"),
    service: ReportService = Depends(get_report_service),
):
    """리포트 내보내기 (txt/md/pdf)."""
    return service.export_report(report_id=report_id, fmt=format)


@router.post("/", response_model=ReportCreateResponse)
def create_report(
    request: ReportCreateRequest,
    service: ReportService = Depends(get_report_service),
    llm_client: LLMClient = Depends(get_llm_client),
):
    """리포트 생성."""
    report = service.create_report(
        session_id=request.session_id,
        analysis_results=request.analysis_results,
        visualizations=request.visualizations,
        insights=request.insights,
        llm_client=llm_client,
    )

    return ReportCreateResponse(
        report_id=report.id,
        session_id=report.session_id,
        version=report.version,
        summary_text=report.summary_text,
        created_at=report.created_at,
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
                "version": item.version,
                "created_at": item.created_at,
            }
            for item in items
        ],
    )


@router.get("/{report_id}", response_model=ReportReadResponse)
def get_report(
    report_id: str,
    service: ReportService = Depends(get_report_service),
):
    """리포트 단건 조회."""
    report = service.get_report(report_id)

    return ReportReadResponse(
        report_id=report.id,
        session_id=report.session_id,
        version=report.version,
        summary_text=report.summary_text,
        payload_json=report.payload_json,
        llm_model=report.llm_model,
        prompt_version=report.prompt_version,
        created_at=report.created_at,
    )
