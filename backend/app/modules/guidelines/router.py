from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from .dependencies import get_guideline_service
from ..rag.dependencies import get_guideline_rag_service
from ..rag.errors import RagEmbeddingError
from ..rag.service import GuidelineRagService
from .schemas import GuidelineActivateResponse, GuidelineBase, GuidelineListResponse
from .service import GuidelineService

router = APIRouter(prefix="/guidelines", tags=["guidelines"])

ALLOWED_GUIDELINE_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
}


def _validate_guideline_pdf(file: UploadFile) -> None:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="파일명이 비어 있습니다.")

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="지침서는 PDF 파일만 업로드할 수 있습니다.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_GUIDELINE_MIME_TYPES:
        raise HTTPException(status_code=400, detail="PDF MIME 타입 파일만 업로드할 수 있습니다.")


def _upload_with_rag_indexing(
    *,
    service: GuidelineService,
    guideline_rag_service: GuidelineRagService,
    file: UploadFile,
):
    try:
        guideline = service.upload_guideline(
            file_stream=file.file,
            original_filename=file.filename or "guideline.pdf",
            display_name=file.filename,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="지침서 업로드 중 오류가 발생했습니다.") from exc

    try:
        guideline_rag_service.index_guideline(guideline)
    except RagEmbeddingError as exc:
        try:
            guideline_rag_service.delete_source(guideline.source_id)
        except Exception:
            pass
        service.delete_guideline(guideline.source_id)
        raise HTTPException(status_code=500, detail="EMBEDDING_ERROR") from exc
    except Exception as exc:
        try:
            guideline_rag_service.delete_source(guideline.source_id)
        except Exception:
            pass
        service.delete_guideline(guideline.source_id)
        raise HTTPException(status_code=500, detail="지침서 업로드 중 오류가 발생했습니다.") from exc

    return guideline


def _delete_with_rag_cleanup(
    *,
    source_id: str,
    service: GuidelineService,
    guideline_rag_service: GuidelineRagService,
) -> None:
    result = service.delete_guideline(source_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])

    try:
        guideline_rag_service.delete_source(source_id)
    except Exception:
        pass


@router.post("/upload", response_model=GuidelineBase)
async def upload_guideline(
    file: UploadFile = File(...),
    service: GuidelineService = Depends(get_guideline_service),
    guideline_rag_service: GuidelineRagService = Depends(get_guideline_rag_service),
):
    _validate_guideline_pdf(file)

    guideline = _upload_with_rag_indexing(
        service=service,
        guideline_rag_service=guideline_rag_service,
        file=file,
    )

    return guideline


@router.get("/", response_model=GuidelineListResponse)
async def list_guidelines(
    skip: int = Query(0, ge=0, description="건너뛸 개수 (offset)"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수 (page size)"),
    service: GuidelineService = Depends(get_guideline_service),
):
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
    guideline_rag_service: GuidelineRagService = Depends(get_guideline_rag_service),
):
    _delete_with_rag_cleanup(
        source_id=source_id,
        service=service,
        guideline_rag_service=guideline_rag_service,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
