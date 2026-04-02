from fastapi import APIRouter, Depends, HTTPException, status

from .dependencies import get_eda_service
from .schemas import EDAProfileResponse
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
