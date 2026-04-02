from fastapi import APIRouter, Depends, HTTPException, status

from .dependencies import get_eda_service
from .schemas import (
    EDAColumnTypesResponse,
    EDAProfileResponse,
    EDAQualityResponse,
    EDAStatsResponse,
    EDASummaryResponse,
)
from .service import EDAService

router = APIRouter(prefix="/eda", tags=["eda"])


@router.get("/{source_id}/profile", response_model=EDAProfileResponse)
def get_eda_profile(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    profile = service.get_profile(source_id)
    if not profile.available:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 프로파일을 생성할 수 없습니다.",
        )
    return profile


@router.get("/{source_id}/summary", response_model=EDASummaryResponse)
def get_eda_summary(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    summary = service.get_summary(source_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 요약을 생성할 수 없습니다.",
        )
    return summary


@router.get("/{source_id}/quality", response_model=EDAQualityResponse)
def get_eda_quality(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    quality = service.get_quality(source_id)
    if quality is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 품질 정보를 생성할 수 없습니다.",
        )
    return quality


@router.get("/{source_id}/columns/types", response_model=EDAColumnTypesResponse)
def get_eda_column_types(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    column_types = service.get_column_types(source_id)
    if column_types is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 컬럼 타입 정보를 생성할 수 없습니다.",
        )
    return column_types


@router.get("/{source_id}/stats", response_model=EDAStatsResponse)
def get_eda_stats(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    stats = service.get_stats(source_id)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 기본 통계를 생성할 수 없습니다.",
        )
    return stats
