from fastapi import APIRouter, Depends, HTTPException

from ..datasets.service import DATASET_READ_ERROR_DETAIL, DatasetReadError
from .dependencies import get_preprocess_service
from .schemas import (
    PreprocessApplyRecommendationRequest,
    PreprocessApplyRequest,
    PreprocessApplyResponse,
)
from .service import PreprocessService

router = APIRouter(prefix="/preprocess", tags=["preprocess"])


@router.post("/apply", response_model=PreprocessApplyResponse)
def apply(
    req: PreprocessApplyRequest,
    service: PreprocessService = Depends(get_preprocess_service),
):
    try:
        return service.apply(source_id=req.source_id, operations=req.operations)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DatasetReadError as exc:
        raise HTTPException(status_code=422, detail=DATASET_READ_ERROR_DETAIL) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/apply-recommendation", response_model=PreprocessApplyResponse)
def apply_recommendation(
    req: PreprocessApplyRecommendationRequest,
    service: PreprocessService = Depends(get_preprocess_service),
):
    try:
        return service.apply_recommendation(
            source_id=req.source_id,
            recommendation=req.recommendation,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except DatasetReadError as exc:
        raise HTTPException(status_code=422, detail=DATASET_READ_ERROR_DETAIL) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
