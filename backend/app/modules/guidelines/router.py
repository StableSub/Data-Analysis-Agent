from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response

from .dependencies import get_guideline_service
from ..rag.dependencies import get_guideline_rag_sync_service
from ..rag.errors import RagEmbeddingError
from ..rag.service import GuidelineRagSyncService
from .schemas import GuidelineActivateResponse, GuidelineBase, GuidelineListResponse
from .service import GuidelineService

router = APIRouter(prefix="/guidelines", tags=["guidelines"])

@router.post("/upload", response_model=GuidelineBase)
async def upload_guideline(
    file: UploadFile = File(...),
    sync_service: GuidelineRagSyncService = Depends(get_guideline_rag_sync_service),
):
    try:
        guideline = sync_service.upload_guideline(
            file_stream=file.file,
            original_filename=file.filename or "guideline.pdf",
            display_name=file.filename,
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RagEmbeddingError as exc:
        raise HTTPException(status_code=500, detail="EMBEDDING_ERROR") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="지침서 업로드 중 오류가 발생했습니다.") from exc

    return guideline


@router.get("/", response_model=GuidelineListResponse)
async def list_guidelines(
    skip: int = Query(0, ge=0, description="건너뛸 개수 (offset)"),
    limit: int = Query(20, ge=1, le=100, description="가져올 개수 (page size)"),
    service: GuidelineService = Depends(get_guideline_service),
):
    items, total = service.list_guidelines(skip=skip, limit=limit)
    return {
        "total": total,
        "items": items,
    }


@router.post("/{source_id}/activate", response_model=GuidelineActivateResponse)
async def activate_guideline(
    source_id: str,
    service: GuidelineService = Depends(get_guideline_service),
):
    guideline = service.activate_guideline(source_id)
    if not guideline:
        raise HTTPException(status_code=404, detail="지침서를 찾을 수 없습니다.")

    return {
        "source_id": guideline.source_id,
        "is_active": guideline.is_active,
        "message": "지침서가 활성화되었습니다.",
    }


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guideline(
    source_id: str,
    sync_service: GuidelineRagSyncService = Depends(get_guideline_rag_sync_service),
):
    deleted = sync_service.delete_guideline(source_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="지침서를 찾을 수 없습니다.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
