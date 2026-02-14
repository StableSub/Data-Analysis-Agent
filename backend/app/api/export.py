from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..domain.export.schemas import CsvExportParams
from ..domain.export.service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


def get_export_service(db: Session = Depends(get_db)) -> ExportService:
    return ExportService(db=db)


@router.post("/csv", response_class=StreamingResponse)
async def download_csv(
    params: CsvExportParams,
    service: ExportService = Depends(get_export_service),
):
    """CSV 다운로드."""
    response, code = service.export_csv(params.result_id)
    if code == "NO_RESULT":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청한 분석 결과를 찾을 수 없습니다.",
        )
    return response
