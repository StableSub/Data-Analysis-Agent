from typing import Optional

from ...ai.agents.client import AgentClient
from ..data_source.repository import DataSourceRepository
from .repository import ChatRepository
from .schemas import ChatHistoryResponse, ChatResponse
from ...rag.service import RagService
from ...rag.types.errors import RagError

DEFAULT_RAG_TOP_K = 3


class ChatService:
    """채팅 세션 생성, 메시지 저장/조회, 간단한 응답 생성을 담당합니다."""

    def __init__(
        self,
        agent: AgentClient,
        repository: ChatRepository,
        data_source_repository: Optional[DataSourceRepository] = None,
        rag_service: Optional[RagService] = None,
    ) -> None:
        self.agent = agent
        self.repository = repository
        self.data_source_repository = data_source_repository
        self.rag_service = rag_service

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

        rag_context = None
        retrieved_chunks = None
        rag_attempted = False
        if data_source_id and self.rag_service:
            try:
                rag_attempted = True
                retrieved_chunks = self.rag_service.query(
                    query=question,
                    top_k=DEFAULT_RAG_TOP_K,
                    source_filter=[data_source_id],
                )
                if retrieved_chunks:
                    rag_context = self.rag_service.build_context(retrieved_chunks)
            except RagError:
                retrieved_chunks = None
                rag_attempted = False

        merged_context = self._build_context_from_source(
            data_source_id=data_source_id,
            fallback_context=context,
            rag_context=rag_context,
            rag_attempted=rag_attempted,
        )
        answer = self.agent.ask(
            session_id=session.id,
            question=question,
            context=merged_context,
        )
        
        self.repository.append_message(session, "user", question)
        self.repository.append_message(session, "assistant", answer)
        if retrieved_chunks and self.rag_service:
            self.rag_service.add_context_links(
                session_id=session.id,
                retrieved=retrieved_chunks,
            )
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
        rag_context: Optional[str],
        rag_attempted: bool,
    ) -> Optional[str]:
        """
        데이터 소스 ID로 파일을 찾아 텍스트를 읽고, 기존 컨텍스트와 합쳐 전달합니다.
        데이터 소스가 없거나 읽을 수 없으면 기존 컨텍스트만 반환합니다.
        """
        pieces = []
        if fallback_context:
            pieces.append(fallback_context)

        if rag_context:
            pieces.append(rag_context)
        elif data_source_id and self.data_source_repository and not rag_attempted:
            dataset = self.data_source_repository.get_by_source_id(data_source_id)
            print(dataset)
            if dataset and dataset.storage_path:
                try:
                    file_text = AgentClient.load_text_from_file(dataset.storage_path)
                    if file_text:
                        pieces.append(file_text)
                except Exception:
                    # 파일을 못 읽더라도 나머지 컨텍스트로 진행
                    pass

        if not pieces:
            return None
        return "\n\n".join(pieces)
