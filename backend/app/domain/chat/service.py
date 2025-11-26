from typing import Optional

from ...ai.llm.client import LLMClient
from ..data_source.repository import DataSourceRepository
from .repository import ChatRepository
from .schemas import ChatHistoryResponse, ChatResponse
from ...ai.orchestrator.chat_flow import ChatFlowOrchestrator
from .models import ChatSession, ChatMessage


class ChatService:
    """채팅 세션 생성, 메시지 저장/조회, 간단한 응답 생성을 담당합니다."""

    def __init__(
        self,
        repository: ChatRepository,
        orchestrator: ChatFlowOrchestrator,
        data_source_repository: Optional[DataSourceRepository] = None,
    ) -> None:
        self.repository = repository
        self.orchestrator = orchestrator
        self.data_source_repository = data_source_repository

    def ask(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        data_source_id: Optional[str] = None,
        context: Optional[str] = None,
    ) -> ChatResponse:
        """질문을 저장하고 간단한 응답을 생성합니다."""
        session = self.repository.get_session(session_id) if session_id else None
        if session is None:
            session = self.repository.create_session(title=question[:60])

        history = self.repository.get_history(session.id)
        merged_context = self._build_context_from_source(
            data_source_id=data_source_id,
            fallback_context=context,
        )
        answer = self.orchestrator.generate_answer(
            session_id=session.id,
            question=question,
            history=history,
            context=merged_context,
        )

        self.repository.append_message(session, "user", question)
        self.repository.append_message(session, "assistant", answer)
        return ChatResponse(answer=answer, session_id=session.id)

    def get_history(self, session_id: int) -> Optional[ChatHistoryResponse]:
        """세션의 전체 히스토리를 반환합니다."""
        session = self.repository.get_session(session_id)
        if not session:
            return None
        messages = self.repository.get_history(session_id)
        return ChatHistoryResponse(session_id=session_id, messages=messages)

    def _build_context_from_source(
        self,
        *,
        data_source_id: Optional[str],
        fallback_context: Optional[str],
    ) -> Optional[str]:
        """
        데이터 소스 ID로 파일을 찾아 텍스트를 읽고, 기존 컨텍스트와 합쳐 전달합니다.
        데이터 소스가 없거나 읽을 수 없으면 기존 컨텍스트만 반환합니다.
        """
        pieces = []
        if fallback_context:
            pieces.append(fallback_context)

        if data_source_id and self.data_source_repository:
            dataset = self.data_source_repository.get_by_source_id(data_source_id)
            print(dataset)
            if dataset and dataset.storage_path:
                try:
                    file_text = LLMClient.load_text_from_file(dataset.storage_path)
                    if file_text:
                        pieces.append(file_text)
                except Exception:
                    # 파일을 못 읽더라도 나머지 컨텍스트로 진행
                    pass

        if not pieces:
            return None
        return "\n\n".join(pieces)
