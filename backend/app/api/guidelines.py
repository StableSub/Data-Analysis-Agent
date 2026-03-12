from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..domain.guideline.repository import GuidelineRepository
from ..domain.guideline.schemas import (
    GuidelineActivateResponse,
    GuidelineBase,
    GuidelineListResponse,
)
from ..domain.guideline.service import GuidelineService

router = APIRouter(
    prefix="/guidelines",
    tags=["guidelines"],
)

ALLOWED_GUIDELINE_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
}


def get_guideline_service(
    db: Session = Depends(get_db),
) -> GuidelineService:
    """DB 세션으로 GuidelineService를 생성한다."""
    repository = GuidelineRepository(db)
    storage_dir = Path(__file__).resolve().parents[3] / "storage" / "guidelines"
    return GuidelineService(repository=repository, storage_dir=storage_dir)


def _validate_guideline_pdf(file: UploadFile) -> None:
    """지침서 업로드 파일이 PDF인지 확인한다."""
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="지침서는 PDF 파일만 업로드할 수 있습니다.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_GUIDELINE_MIME_TYPES:
        raise HTTPException(status_code=400, detail="PDF MIME 타입 파일만 업로드할 수 있습니다.")


@router.post("/upload", response_model=GuidelineBase)
async def upload_guideline(
    file: UploadFile = File(...),
    service: GuidelineService = Depends(get_guideline_service),
):
    """지침서 PDF를 업로드하고 메타데이터를 저장한다."""
    _validate_guideline_pdf(file)

    try:
        guideline = service.upload_guideline(
            file_stream=file.file,
            original_filename=file.filename or "guideline.pdf",
            display_name=file.filename,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="지침서 업로드 중 오류가 발생했습니다.")

    return guideline


@router.get("/", response_model=GuidelineListResponse)
async def list_guidelines(
    skip: int = Query(0, ge=0, description="건너뛸 개수 (offset)"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수 (page size)"),
    service: GuidelineService = Depends(get_guideline_service),
):
    """지침서 목록을 조회한다."""
    items = service.list_guidelines(skip=skip, limit=limit)
    total = len(service.list_guidelines(skip=0, limit=10_000_000))

    return {
        "total": total,
        "items": items,
    }


@router.post("/{source_id}/activate", response_model=GuidelineActivateResponse)
async def activate_guideline(
    source_id: str,
    service: GuidelineService = Depends(get_guideline_service),
):
    """특정 지침서를 활성화한다."""
    result = service.activate_guideline(source_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    guideline = result["guideline"]
    return {
        "source_id": guideline.source_id,
        "is_active": guideline.is_active,
        "message": result["message"],
    }


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guideline(
    source_id: str,
    service: GuidelineService = Depends(get_guideline_service),
):
    """지침서를 삭제한다."""
    result = service.delete_guideline(source_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    return Response(status_code=status.HTTP_204_NO_CONTENT)
