from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.domain.preprocess.schemas import (
    PreprocessPreviewResponse,
    PreprocessPreviewRequest,
    PreprocessApplyRequest,
    PreprocessApplyResponse,
)
from backend.app.domain.preprocess.service import PreprocessService

router = APIRouter(prefix="/preprocess", tags=["preprocess"])


@router.post("/preview", response_model=PreprocessPreviewResponse)
def preview(req: PreprocessPreviewRequest, db: Session = Depends(get_db)):
    """
    전처리 UI 진입 시 데이터 컬럼/타입/샘플 미리보기 제공
    """
    try:
        return PreprocessService(db).preview(
            dataset_id=req.dataset_id,
            version_id=req.version_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/apply", response_model=PreprocessApplyResponse)
def apply(req: PreprocessApplyRequest, db: Session = Depends(get_db)):
    """
    GUI에서 설정한 전처리 작업을 실제 데이터에 적용하고
    새로운 데이터 버전을 생성
    """
    try:
        return PreprocessService(db).apply(
            dataset_id=req.dataset_id,
            base_version_id=req.base_version_id,
            operations=req.operations,
            created_by=req.created_by,
            note=req.note,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
