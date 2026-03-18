from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from .dependencies import get_export_service
from .schemas import CsvExportParams
from .service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


@router.post("/csv", response_class=StreamingResponse)
async def download_csv(
    params: CsvExportParams,
    service: ExportService = Depends(get_export_service),
):
    byte_stream, filename = service.export_csv(params.result_id)
    if byte_stream is None or filename is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="요청한 분석 결과를 찾을 수 없습니다.",
        )

    response = StreamingResponse(byte_stream, media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
