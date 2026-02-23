from typing import Any, AsyncIterator, Dict, Optional

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

    async def ask(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        model_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> ChatResponse:
        """질문을 저장하고 모델 응답을 반환한다."""
        done_payload: Dict[str, Any] | None = None
        async for event in self.ask_stream(
            question=question,
            session_id=session_id,
            model_id=model_id,
            source_id=source_id,
        ):
            if event.get("event") == "done":
                payload = event.get("data")
                if isinstance(payload, dict):
                    done_payload = payload

        if done_payload is None:
            raise RuntimeError("chat stream finished without done event")

        answer = done_payload.get("answer")
        session_id_value = done_payload.get("session_id")
        thought_steps = done_payload.get("thought_steps")
        if not isinstance(session_id_value, int):
            raise RuntimeError("chat stream finished without session id")
        return ChatResponse(
            answer=str(answer) if isinstance(answer, str) else "",
            session_id=session_id_value,
            thought_steps=thought_steps if isinstance(thought_steps, list) else [],
        )

    async def ask_stream(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        model_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """질문을 스트리밍 처리하고 SSE 이벤트용 페이로드를 반환한다."""
        session = self.repository.get_session(session_id) if session_id else None
        if session is None:
            session = self.repository.create_session(title=question[:60])

        dataset = (
            self.data_source_repository.get_by_source_id(source_id)
            if source_id
            else None
        )

        self.repository.append_message(session, "user", question)
        yield {"event": "session", "data": {"session_id": session.id}}

        answer_parts: list[str] = []
        thought_steps: list[Dict[str, Any]] = []
        preprocess_result: Dict[str, Any] | None = None
        visualization_result: Dict[str, Any] | None = None
        async for event in self.agent.astream_with_trace(
            session_id=str(session.id),
            question=question,
            dataset=dataset,
            model_id=model_id,
        ):
            event_type = event.get("type")
            if event_type == "thought":
                step = event.get("step")
                if isinstance(step, dict):
                    thought_steps.append(step)
                    yield {"event": "thought", "data": step}
            elif event_type == "chunk":
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    answer_parts.append(delta)
                    yield {"event": "chunk", "data": {"delta": delta}}
            elif event_type == "done":
                final_answer = event.get("answer")
                if isinstance(final_answer, str):
                    answer_parts = [final_answer]
                final_steps = event.get("thought_steps")
                if isinstance(final_steps, list):
                    thought_steps = [step for step in final_steps if isinstance(step, dict)]
                event_preprocess = event.get("preprocess_result")
                if isinstance(event_preprocess, dict):
                    preprocess_result = event_preprocess
                event_visualization = event.get("visualization_result")
                if isinstance(event_visualization, dict):
                    visualization_result = event_visualization

        final_answer = "".join(answer_parts).strip()
        if not final_answer:
            final_answer = "응답을 생성하지 못했습니다."

        self.repository.append_message(session, "assistant", final_answer)
        done_data: Dict[str, Any] = {
            "answer": final_answer,
            "session_id": session.id,
            "thought_steps": thought_steps,
            "preprocess_result": preprocess_result,
        }
        if isinstance(visualization_result, dict):
            done_data["visualization_result"] = visualization_result
        yield {
            "event": "done",
            "data": done_data,
        }

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
