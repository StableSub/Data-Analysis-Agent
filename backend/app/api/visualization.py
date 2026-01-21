from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path

from ..core.db import get_db
from ..domain.data_source.repository import DataSourceRepository
from ..domain.data_source.service import DataSourceService
from ..domain.data_source.schemas import ManualVizRequest, ManualVizResponse

router = APIRouter(
    prefix="/vizualization",
    tags=["visualization"],
)

def get_data_source_service(db: Session = Depends(get_db)) -> DataSourceService:
    repository = DataSourceRepository(db)
    storage_dir = Path("storage") / "datasets"
    return DataSourceService(repository=repository, storage_dir=storage_dir)

@router.post("/manual", response_model=ManualVizResponse)
async def create_manual_visualization(
    request: ManualVizRequest,
    service: DataSourceService = Depends(get_data_source_service)
):
    """
    사용자 정의 설정을 기반으로 시각화 데이터 생성
    """
    result = service.get_manual_viz_data(request)

    if "error" in result:
        error_code = result["error"]
        if error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result["message"])
        elif error_code == "INVALID_COLUMN":
            raise HTTPException(status_code=400, detail="존재하지 않는 컬럼이 포함되어 있습니다.")
        elif error_code == "NO_DATA":
            raise HTTPException(status_code=422, detail="데이터가 부족하여 시각화할 수 없습니다.")
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    return result