from pathlib import Path
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..domain.data_source.repository import DataSourceRepository
from ..domain.data_source.schemas import DatasetUploadRequest, DatasetUploadResponse
from ..domain.data_source.service import DataSourceService

router = APIRouter(
    prefix="/datasets",
    tags=["datasets"],
)

def get_data_source_service(
    db: Session = Depends(get_db),
) -> DataSourceService:
    """
    DB 세션으로 Repository 생성
    """
    repository = DataSourceRepository(db)
    storage_dir = Path("storage") / "datasets"
    return DataSourceService(repository=repository, storage_dir=storage_dir)


@router.post("/", response_model=DatasetUploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    options: DatasetUploadRequest = Depends(),
    service: DataSourceService = Depends(get_data_source_service),
):
    """
    데이터셋 파일 업로드 엔드포인트
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    try:
        dataset = service.upload_dataset(
            file_stream=file.file,
            original_filename=file.filename,
            display_name=file.filename,
            encoding=options.encoding,
            delimiter=options.delimiter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다.")

    return dataset