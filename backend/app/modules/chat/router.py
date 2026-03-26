import json
from typing import Any, AsyncIterator, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from .dependencies import get_chat_service
from .schemas import (
    ChatHistoryResponse,
    ChatRequest,
    PendingApprovalResponse,
    ResumeRunRequest,
)
from .service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

def _stream_response(events: AsyncIterator[Dict[str, Any]]) -> StreamingResponse:
    async def event_generator():
        try:
            async for event in events:
                name = str(event.get("event") or "message")
                data = event.get("data")
                payload = data if isinstance(data, dict) else {"value": data}
                yield _format_sse(name, payload)
        except Exception as exc:
            yield _format_sse("error", {"message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )

@router.post("/stream")
async def ask_chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    return _stream_response(
        chat_service.ask_stream(
            question=request.question,
            session_id=request.session_id,
            model_id=request.model_id,
            source_id=request.source_id,
        )
    )

@router.post("/{session_id}/runs/{run_id}/resume")
async def resume_chat_run(
    session_id: int,
    run_id: str,
    request: ResumeRunRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    return _stream_response(
        chat_service.resume_run_stream(
            session_id=session_id,
            run_id=run_id,
            decision=request.decision,
            stage=request.stage,
            instruction=request.instruction,
        )
    )

@router.get("/runs/{run_id}/pending-approval", response_model=PendingApprovalResponse)
async def get_pending_approval(
    run_id: str,
    chat_service: ChatService = Depends(get_chat_service),
):
    pending = chat_service.get_pending_approval(run_id=run_id)
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="pending approval not found",
        )
    return pending

@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_history(
    session_id: int,
    chat_service: ChatService = Depends(get_chat_service),
):
    history = chat_service.get_history(session_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션을 찾을 수 없습니다.",
        )
    return history

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    session_id: int,
    chat_service: ChatService = Depends(get_chat_service),
):
    deleted = chat_service.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="세션을 찾을 수 없습니다.",
        )
    return None
