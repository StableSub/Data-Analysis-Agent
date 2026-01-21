from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..dependencies import get_rag_service
from ..domain.data_source.repository import DataSourceRepository
from ..domain.data_source.schemas import (
    DatasetUploadRequest,
    DatasetUploadResponse,
    DatasetListResponse,
    DatasetRead,
    DatasetMetadataResponse,
    DatasetMetadataUpdateRequest,
    DatasetMetadataUpdateResponse,
)
from ..domain.data_source.service import DataSourceService
from ..rag.service import RagService
from ..rag.types.errors import RagEmbeddingError

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
    rag_service: RagService = Depends(get_rag_service),
    workspace_id: Optional[str] = Query(
        None,
        description="업로드되는 데이터셋이 속한 워크스페이스 ID",
    ),
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
            workspace_id=workspace_id,
        )
        rag_service.index_dataset(dataset)
    except RagEmbeddingError:
        raise HTTPException(status_code=500, detail="EMBEDDING_ERROR")
    except Exception:
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다.")

    return {
        "id": dataset.id,
        "source_id": dataset.source_id,
        "workspace_id": dataset.workspace_id,
        "filename": dataset.filename,
        "filesize": dataset.filesize,
        "uploaded_at": dataset.uploaded_at,
        "metadata": {
            "encoding": dataset.encoding,
            "delimiter": dataset.delimiter,
        }
    }


@router.get("/", response_model=DatasetListResponse)
async def list_datasets(
    workspace_id: Optional[str] = Query(
        None,
        description="필터링할 워크스페이스 ID (없으면 전체)",
    ),
    skip: int = Query(0, ge=0, description="건너뛸 개수 (offset)"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수 (page size)"),
    service: DataSourceService = Depends(get_data_source_service),
):
    """
    데이터 소스 목록 조회
    - workspace_id 기준 필터 (옵션)
    - skip / limit 기반 간단 페이지네이션
    """
    # 페이지 데이터
    items = service.list_datasets(
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
    )

    # total 계산을 위해 전체 개수를 한 번 더 조회
    all_for_count = service.list_datasets(
        workspace_id=workspace_id,
        skip=0,
        limit=10_000_000,
    )
    total = len(all_for_count)

    return {
        "total": total,
        "items": items,
    }


@router.get("/{dataset_id}", response_model=DatasetRead)
async def get_dataset_detail(
    dataset_id: int,
    service: DataSourceService = Depends(get_data_source_service),
):
    """
    단일 데이터 소스 상세 조회
    """
    detail_data = service.get_dataset_detail(dataset_id)
    if not detail_data:
        raise HTTPException(status_code=404, detail="데이터셋을 찾을 수 없습니다.")

    dataset = detail_data["dataset"]
    return dataset

@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    source_id: str,
    service: DataSourceService = Depends(get_data_source_service),
    rag_service: RagService = Depends(get_rag_service),
):
    """
    데이터 소스 삭제 엔드포인트 (안전 삭제 처리 포함)
    
    - 세션에서 사용 중인 파일은 삭제하지 않고 오류 반환
    - 성공 시: 204 No Content 반환, 본문 없음
    - 삭제할 파일이 없는 경우: 404 NOT_FOUND
    - 사용 중인 파일: 409 CONFLICT (또는 400 BAD_REQUEST)
    
    Args:
        source_id: 삭제할 데이터 소스의 고유 ID
    """
    result = service.delete_dataset(source_id)
    
    # 데이터셋이 존재하지 않음
    if not result["success"] and not result["in_use"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    
    # 데이터셋이 세션에서 사용 중임 (안전 삭제 처리)
    if result["in_use"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=result["message"]
        )
    
    # 성공 시 204 No Content 반환 (본문 없음)
    try:
        rag_service.delete_source(source_id)
    except Exception:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{source_id}/meta", response_model=DatasetMetadataResponse)
async def get_dataset_metadata(
    source_id: str,
    service: DataSourceService = Depends(get_data_source_service),
):
    """
    데이터 소스 메타데이터 조회
    
    Args:
        source_id: 데이터 소스 ID
        
    Returns:
        DatasetMetadataResponse: 인코딩, 구분자 등 메타데이터
    """
    metadata = service.get_dataset_metadata(source_id)
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없습니다."
        )
    
    return metadata


@router.patch("/{source_id}/meta", response_model=DatasetMetadataUpdateResponse)
async def update_dataset_metadata(
    source_id: str,
    request: DatasetMetadataUpdateRequest,
    service: DataSourceService = Depends(get_data_source_service),
):
    """
    데이터 소스 메타데이터 수동 수정
    
    필요 시 사용자가 인코딩, 구분자, 헤더 존재 여부를 수동으로 보정 가능
    
    Args:
        source_id: 데이터 소스 ID
        request: 수정할 필드 (encoding, delimiter, has_header)
        
    Returns:
        DatasetMetadataUpdateResponse: 수정 결과
    """
    result = service.update_dataset_metadata(
        source_id=source_id,
        encoding=request.encoding,
        delimiter=request.delimiter,
        has_header=request.has_header
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없습니다."
        )
    
    return result
