from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from ..rag.dependencies import get_rag_service
from ..rag.errors import RagEmbeddingError
from ..rag.service import RagService
from .schemas import DatasetBase, DatasetListResponse, DatasetSampleResponse
from .service import DataSourceService, get_data_source_service

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/", response_model=DatasetBase)
async def upload_dataset(
    file: UploadFile = File(...),
    service: DataSourceService = Depends(get_data_source_service),
    rag_service: RagService = Depends(get_rag_service),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    try:
        dataset = service.upload_dataset(
            file_stream=file.file,
            original_filename=file.filename,
            display_name=file.filename,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다.")

    try:
        rag_service.index_dataset(dataset)
    except RagEmbeddingError:
        try:
            rag_service.delete_source(dataset.source_id)
        except Exception:
            pass
        service.delete_dataset(dataset.source_id)
        raise HTTPException(status_code=500, detail="EMBEDDING_ERROR")
    except Exception:
        try:
            rag_service.delete_source(dataset.source_id)
        except Exception:
            pass
        service.delete_dataset(dataset.source_id)
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다.")

    return {
        "id": dataset.id,
        "source_id": dataset.source_id,
        "filename": dataset.filename,
        "storage_path": dataset.storage_path,
        "filesize": dataset.filesize,
    }


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    skip: int = Query(0, ge=0, description="건너뛸 개수 (offset)"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수 (page size)"),
    service: DataSourceService = Depends(get_data_source_service),
):
    items = service.list_datasets(skip=skip, limit=limit)
    total = len(service.list_datasets(skip=0, limit=10_000_000))
    return {"total": total, "items": items}


@router.get("/{dataset_id}", response_model=DatasetBase)
async def get_dataset_detail(
    dataset_id: int,
    service: DataSourceService = Depends(get_data_source_service),
):
    detail_data = service.get_dataset_detail(dataset_id)
    if not detail_data:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다.")

    return detail_data["dataset"]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    source_id: str,
    service: DataSourceService = Depends(get_data_source_service),
    rag_service: RagService = Depends(get_rag_service),
):
    result = service.delete_dataset(source_id)
    if result["success"]:
        try:
            rag_service.delete_source(source_id)
        except Exception:
            pass
    if not result["success"]:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["message"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{source_id}/sample", response_model=DatasetSampleResponse)
async def get_dataset_sample(
    source_id: str,
    service: DataSourceService = Depends(get_data_source_service),
):
    sample_data = service.get_dataset_sample(source_id, n_rows=5)
    if not sample_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 샘플 데이터를 읽을 수 없습니다.",
        )
    return sample_data
