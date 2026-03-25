from fastapi import APIRouter, Depends, HTTPException

from .dependencies import get_visualization_service
from .schemas import ManualVizRequest, ManualVizResponse
from .service import VisualizationService

router = APIRouter(prefix="/vizualization", tags=["visualization"])


@router.post("/manual", response_model=ManualVizResponse)
async def create_manual_visualization(
    request: ManualVizRequest,
    service: VisualizationService = Depends(get_visualization_service),
):
    result = service.get_manual_viz_data(request)

    if "error" in result:
        error_code = result["error"]
        if error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        if error_code == "INVALID_COLUMN":
            raise HTTPException(status_code=400, detail="존재하지 않는 컬럼이 포함되어 있습니다.")
        if error_code == "NO_DATA":
            raise HTTPException(status_code=422, detail="데이터가 부족하여 시각화할 수 없습니다.")
        raise HTTPException(status_code=500, detail=result["message"])

    return result
