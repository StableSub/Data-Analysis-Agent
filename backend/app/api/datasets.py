from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..domain.data_source.repository import DataSourceRepository
from ..domain.data_source.schemas import (
    DatasetUploadRequest,
    DatasetUploadResponse,
    DatasetListResponse,
    DatasetRead,
)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 중 오류가 발생했습니다.")

    return dataset



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
    return Response(status_code=status.HTTP_204_NO_CONTENT)