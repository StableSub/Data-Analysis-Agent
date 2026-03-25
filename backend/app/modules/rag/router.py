from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from .dependencies import get_rag_service
from .errors import RagEmbeddingError, RagNotIndexedError, RagSearchError
from .schemas import RagDeleteResponse, RagQueryRequest, RagQueryResponse, RagRetrievedChunk
from .service import RagService

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(
    request: RagQueryRequest,
    rag_service: RagService = Depends(get_rag_service),
):
    try:
        result = await rag_service.answer_query(
            query=request.query,
            top_k=request.top_k,
            source_filter=request.source_filter,
        )
    except RagNotIndexedError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.code) from exc
    except RagEmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.code) from exc
    except RagSearchError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.code) from exc

    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    answer, retrieved = result
    retrieved_chunks = [
        RagRetrievedChunk(
            source_id=item.source_id,
            chunk_id=item.chunk_id,
            score=item.score,
            snippet=item.content[:200],
        )
        for item in retrieved
    ]
    return RagQueryResponse(
        answer=answer,
        retrieved_chunks=retrieved_chunks,
        executed_at=datetime.now(timezone.utc),
    )


@router.delete("/sources/{source_id}", response_model=RagDeleteResponse)
async def delete_rag_source(
    source_id: str,
    rag_service: RagService = Depends(get_rag_service),
):
    rag_service.delete_source(source_id)
    return RagDeleteResponse(success=True)
