from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.domain.preprocess.schemas import PreprocessApplyRequest, PreprocessApplyResponse
from backend.app.domain.preprocess.service import PreprocessService

router = APIRouter(prefix="/preprocess", tags=["preprocess"])


@router.post("/apply", response_model=PreprocessApplyResponse)
def apply(req: PreprocessApplyRequest, db: Session = Depends(get_db)):
    """전처리 연산을 선택한 데이터셋에 적용한다."""
    try:
        return PreprocessService(db).apply(
            dataset_id=req.dataset_id,
            operations=req.operations,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
