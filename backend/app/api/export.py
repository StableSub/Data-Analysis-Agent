from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..domain.export.schemas import CsvExportParams, ChartExportParams
from ..domain.export.service import ExportService

router = APIRouter(
    prefix="/export",
    tags=["export"],
)

def get_export_service(db: Session = Depends(get_db)):
    return ExportService(db=db)

@router.post("/csv", response_class=StreamingResponse)
async def download_csv(
    params: CsvExportParams = Depends(),
    service: ExportService = Depends(get_export_service)
):
    """
    CSV 다운로드
    """
    if not params.result_id and not params.view_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="result_id 또는 view_token이 필요합니다."
        )

    response, code = service.export_csv(params)
    
    if code == "NO_RESULT":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청한 분석 결과를 찾을 수 없습니다."
        )
    
    return response


@router.get("/chart/png", response_class=StreamingResponse)
async def download_chart_png(
    params: ChartExportParams = Depends(),
    service: ExportService = Depends(get_export_service)
):
    """
    차트 PNG 다운로드
    """
    response, code = service.export_chart(params)
    
    if code == "NO_RESULT":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청한 차트를 찾을 수 없습니다."
        )
        
    return response