from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.domain.preprocess.schemas import PreprocessApplyRequest, PreprocessApplyResponse
from backend.app.domain.preprocess.service import PreprocessService
from backend.app.domain.preprocess.state import PreprocessState, get_preprocess_state

router = APIRouter(prefix="/preprocess", tags=["preprocess"])


@router.post("/apply", response_model=PreprocessApplyResponse)
def apply(req: PreprocessApplyRequest, db: Session = Depends(get_db), state: PreprocessState = Depends(get_preprocess_state)):
    """전처리 연산을 선택한 source_id 데이터셋에 적용한다."""
    try:
        return PreprocessService(db).apply(
            source_id=req.source_id,
            operations=req.operations,
        )
        state.record(resp)
        return resp
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
