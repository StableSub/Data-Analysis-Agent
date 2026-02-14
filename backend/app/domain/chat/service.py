from typing import Optional

from ...ai.agents.client import AgentClient
from ..data_source.repository import DataSourceRepository
from .repository import ChatRepository
from .schemas import ChatHistoryResponse, ChatResponse


class ChatService:
    """채팅 최소 서비스: 질문 응답/히스토리 조회/세션 삭제."""

    def __init__(
        self,
        agent: AgentClient,
        repository: ChatRepository,
        data_source_repository: DataSourceRepository,
    ) -> None:
        self.agent = agent
        self.repository = repository
        self.data_source_repository = data_source_repository

    def ask(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        model_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> ChatResponse:
        """질문을 저장하고 모델 응답을 반환한다."""
        session = self.repository.get_session(session_id) if session_id else None
        if session is None:
            session = self.repository.create_session(title=question[:60])

        dataset = (
            self.data_source_repository.get_by_source_id(source_id)
            if source_id
            else None
        )

        answer = self.agent.ask(
            session_id=str(session.id),
            question=question,
            dataset=dataset,
            model_id=model_id,
        )
        self.repository.append_message(session, "user", question)
        self.repository.append_message(session, "assistant", answer)
        return ChatResponse(answer=answer, session_id=session.id)

    def get_history(self, session_id: int) -> Optional[ChatHistoryResponse]:
        """세션의 전체 메시지 히스토리를 반환한다."""
        session = self.repository.get_session(session_id)
        if not session:
            return None
        messages = self.repository.get_history(session_id)
        return ChatHistoryResponse(session_id=session_id, messages=messages)

    def delete_session(self, session_id: int) -> bool:
        """세션을 삭제한다."""
        return self.repository.delete_session(session_id)
