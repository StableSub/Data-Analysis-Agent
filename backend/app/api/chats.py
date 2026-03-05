import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..dependencies import get_chat_service
from ..domain.chat.schemas import ChatHistoryResponse, ChatRequest, ChatResponse
from ..domain.chat.service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


def _format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/", response_model=ChatResponse)
async def ask_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    질문을 저장하고 간단한 응답을 반환합니다.
    세션 ID가 없으면 자동으로 새 세션을 생성합니다.
    """
    return await chat_service.ask(
        question=request.question,
        session_id=request.session_id,
        model_id=request.model_id,
        source_id=request.source_id,
    )


@router.post("/stream")
async def ask_chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """질문을 SSE 스트리밍 형태로 반환한다."""

    async def event_generator():
        try:
            async for event in chat_service.ask_stream(
                question=request.question,
                session_id=request.session_id,
                model_id=request.model_id,
                source_id=request.source_id,
            ):
                name = str(event.get("event") or "message")
                data = event.get("data")
                payload = data if isinstance(data, dict) else {"value": data}
                yield _format_sse(name, payload)
        except Exception as exc:
            yield _format_sse("error", {"message": str(exc)})

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_history(
    session_id: int,
    chat_service: ChatService = Depends(get_chat_service),
):
    """세션의 모든 메시지를 시간순으로 반환합니다."""
    history = chat_service.get_history(session_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다."
        )
    return history


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    session_id: int,
    chat_service: ChatService = Depends(get_chat_service),
):
    """세션을 삭제합니다."""
    deleted = chat_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다."
        )
    return None
