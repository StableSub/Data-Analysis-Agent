from fastapi import APIRouter, Depends, HTTPException, Query, status

from .dependencies import get_report_service
from .schemas import ReportBase, ReportCreateRequest, ReportListResponse
from .service import ReportService

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/", response_model=ReportBase)
async def create_report(
    request: ReportCreateRequest,
    service: ReportService = Depends(get_report_service),
):
    try:
        report = await service.create_report_from_request(
            session_id=request.session_id,
            analysis_results=request.analysis_results,
            visualizations=request.visualizations,
            insights=request.insights,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

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
    try:
        report = service.get_report(report_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ReportBase(
        report_id=report.id,
        session_id=report.session_id,
        summary_text=report.summary_text,
    )
