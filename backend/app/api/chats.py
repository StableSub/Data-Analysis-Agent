from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_chat_service
from ..domain.chat.schemas import ChatHistoryResponse, ChatRequest, ChatResponse
from ..domain.chat.service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse)
async def ask_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    질문을 저장하고 간단한 응답을 반환합니다.
    세션 ID가 없으면 자동으로 새 세션을 생성합니다.
    """
    return chat_service.ask(
        question=request.question,
        session_id=request.session_id,
        context=request.context,
        data_source_id=request.data_source_id,
        model_id=request.model_id,
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
