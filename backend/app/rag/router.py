from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from ..ai.agents.client import AgentClient
from ..dependencies import get_agent, get_rag_service
from .service import RagService
from .types.errors import RagEmbeddingError, RagNotIndexedError, RagSearchError
from .types.schemas import (
    RagDeleteResponse,
    RagQueryRequest,
    RagQueryResponse,
    RagRetrievedChunk,
)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
async def rag_query(
    request: RagQueryRequest,
    rag_service: RagService = Depends(get_rag_service),
    agent: AgentClient = Depends(get_agent),
):
    """
    [RAG 검색 및 답변]
    사용자의 질문을 받아 벡터 DB를 검색하고 LLM을 통해 답변을 생성.

    - 성공 시: 200 OK와 답변 및 근거 청크 반환
    - 데이터 없음: 204 No Content
    - 에러 발생: 404(인덱스 없음), 500(내부 연산 오류)
    """
    try:
        retrieved = rag_service.query(
            query=request.query,
            top_k=request.top_k,
            source_filter=request.source_filter,
        )
    except RagNotIndexedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=exc.code
        ) from exc
    except RagEmbeddingError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.code
        ) from exc
    except RagSearchError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.code
        ) from exc

    if not retrieved:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    context = rag_service.build_context(retrieved)
    answer = agent.ask(question=request.query, context=context)

    retrieved_chunks = [
        RagRetrievedChunk(
            source_id=item.source_id,
            chunk_id=item.chunk_id,
            score=item.score,
            snippet=item.content[:200],
        )
        for item in retrieved
    ]
    executed_at = datetime.now(timezone.utc)
    return RagQueryResponse(
        answer=answer,
        retrieved_chunks=retrieved_chunks,
        executed_at=executed_at,
    )


@router.delete("/sources/{source_id}", response_model=RagDeleteResponse)
async def delete_rag_source(
    source_id: str,
    rag_service: RagService = Depends(get_rag_service),
):
    rag_service.delete_source(source_id)
    return RagDeleteResponse(success=True)
