from fastapi import APIRouter, Depends, HTTPException

from .dependencies import get_preprocess_service
from .schemas import PreprocessApplyRequest, PreprocessApplyResponse
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
