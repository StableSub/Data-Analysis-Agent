from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
import pandas as pd

from .dependencies import get_dataset_service
from ..rag.dependencies import get_dataset_rag_sync_service
from ..rag.errors import RagEmbeddingError
from ..rag.service import DatasetRagSyncService
from .schemas import DatasetBase, DatasetListResponse, DatasetSampleResponse
from .service import DatasetService

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/", response_model=DatasetBase)
async def upload_dataset(
    file: UploadFile = File(...),
    sync_service: DatasetRagSyncService = Depends(get_dataset_rag_sync_service),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    try:
        dataset = sync_service.upload_dataset(
            file_stream=file.file,
            original_filename=file.filename,
            display_name=file.filename,
        )
    except RagEmbeddingError as exc:
        raise HTTPException(status_code=500, detail="EMBEDDING_ERROR") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다.") from exc

    return dataset


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    skip: int = Query(0, ge=0, description="건너뛸 개수 (offset)"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수 (page size)"),
    service: DatasetService = Depends(get_dataset_service),
):
    items, total = service.list_datasets(skip=skip, limit=limit)
    return {"total": total, "items": items}


@router.get("/{source_id}", response_model=DatasetBase)
async def get_dataset_detail(
    source_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    dataset = service.get_dataset_detail(source_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다.")

    return dataset


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    source_id: str,
    sync_service: DatasetRagSyncService = Depends(get_dataset_rag_sync_service),
):
    deleted = sync_service.delete_dataset(source_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="데이터셋을 찾을 수 없습니다.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{source_id}/sample", response_model=DatasetSampleResponse)
async def get_dataset_sample(
    source_id: str,
    service: DatasetService = Depends(get_dataset_service),
):
    try:
        sample_data = service.get_dataset_sample(source_id, n_rows=5)
    except (FileNotFoundError, UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="데이터셋 샘플을 읽을 수 없습니다.",
        ) from exc

    if not sample_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없습니다.",
        )
    return sample_data
