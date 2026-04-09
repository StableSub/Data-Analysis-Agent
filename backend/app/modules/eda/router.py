from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..datasets.service import DATASET_READ_ERROR_DETAIL, DatasetReadError
from .dependencies import get_eda_service
from .schemas import (
    EDAAISummaryResponse,
    EDAColumnTypesResponse,
    EDACorrelationsResponse,
    EDADistributionResponse,
    EDAOutliersResponse,
    EDAProfileResponse,
    EDAQualityResponse,
    EDAStatsResponse,
    EDASummaryResponse,
    PreprocessRecommendationResponse,
)
from .service import EDAInvalidRequestError, EDAService, EDAUnsupportedRequestError

router = APIRouter(prefix="/eda", tags=["eda"])


def _raise_dataset_read_http_error(exc: DatasetReadError) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=DATASET_READ_ERROR_DETAIL,
    ) from exc


@router.get("/{source_id}/profile", response_model=EDAProfileResponse)
def get_eda_profile(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    try:
        profile = service.get_profile(source_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
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
    try:
        summary = service.get_summary(source_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
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
    try:
        quality = service.get_quality(source_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
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
    try:
        column_types = service.get_column_types(source_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
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
    try:
        stats = service.get_stats(source_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 기본 통계를 생성할 수 없습니다.",
        )
    return stats


@router.get("/{source_id}/correlations/top", response_model=EDACorrelationsResponse)
def get_eda_top_correlations(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    try:
        correlations = service.get_top_correlations(source_id, limit=3)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
    if correlations is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 상관관계를 생성할 수 없습니다.",
        )
    return correlations


@router.get("/{source_id}/outliers", response_model=EDAOutliersResponse)
def get_eda_outliers(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    try:
        outliers = service.get_outliers(source_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
    if outliers is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 이상치 정보를 생성할 수 없습니다.",
        )
    return outliers


@router.get("/{source_id}/distribution", response_model=EDADistributionResponse)
def get_eda_distribution(
    source_id: str,
    column: str = Query(..., description="분포를 조회할 컬럼명"),
    bins: int = Query(10, ge=1, le=50, description="히스토그램 bin 개수"),
    top_n: int = Query(10, ge=1, le=20, description="범주형 상위 노출 개수"),
    service: EDAService = Depends(get_eda_service),
):
    try:
        distribution = service.get_distribution(
            source_id,
            column=column,
            bins=bins,
            top_n=top_n,
        )
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
    except EDAInvalidRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EDAUnsupportedRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if distribution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 분포 데이터를 생성할 수 없습니다.",
        )
    return distribution


@router.get(
    "/{source_id}/preprocess-recommendations",
    response_model=PreprocessRecommendationResponse,
)
def get_eda_preprocess_recommendations(
    source_id: str,
    service: EDAService = Depends(get_eda_service),
):
    try:
        recommendation_response = service.get_preprocess_recommendation_response(source_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
    if recommendation_response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 전처리 추천을 생성할 수 없습니다.",
        )
    return recommendation_response


@router.get("/{source_id}/insights", response_model=EDAAISummaryResponse)
def get_eda_insights(
    source_id: str,
    model_id: str | None = Query(default=None, description="Optional model override"),
    service: EDAService = Depends(get_eda_service),
):
    try:
        summary = service.get_ai_summary(source_id, model_id=model_id)
    except DatasetReadError as exc:
        _raise_dataset_read_http_error(exc)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="데이터셋을 찾을 수 없거나 AI 요약을 생성할 수 없습니다.",
        )
    return summary
