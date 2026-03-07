import uuid
from typing import Any, AsyncIterator, Dict, Optional

from ...ai.agents.client import AgentClient
from ..data_source.repository import DataSourceRepository
from .repository import ChatRepository
from .schemas import ChatHistoryResponse, ChatResponse, PendingApprovalResponse


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
        approval_payload: Dict[str, Any] | None = None
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
            elif event.get("event") == "approval_required":
                payload = event.get("data")
                if isinstance(payload, dict):
                    approval_payload = payload

        if approval_payload is not None:
            session_id_value = approval_payload.get("session_id")
            run_id = approval_payload.get("run_id")
            thought_steps = approval_payload.get("thought_steps")
            pending_approval = approval_payload.get("pending_approval")
            if not isinstance(session_id_value, int):
                raise RuntimeError("chat stream finished without session id")
            return ChatResponse(
                answer="",
                session_id=session_id_value,
                run_id=run_id if isinstance(run_id, str) else None,
                thought_steps=thought_steps if isinstance(thought_steps, list) else [],
                pending_approval=pending_approval if isinstance(pending_approval, dict) else None,
            )

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
            run_id=done_payload.get("run_id") if isinstance(done_payload.get("run_id"), str) else None,
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
        run_id = uuid.uuid4().hex
        yield {"event": "session", "data": {"session_id": session.id, "run_id": run_id}}

        async for event in self._relay_agent_events(
            session_id=session.id,
            run_id=run_id,
            agent_stream=self.agent.astream_with_trace(
                session_id=str(session.id),
                run_id=run_id,
                question=question,
                dataset=dataset,
                model_id=model_id,
            ),
            append_assistant_message=True,
            session=session,
        ):
            yield event

    async def resume_run_stream(
        self,
        *,
        session_id: int,
        run_id: str,
        decision: str,
        stage: str,
        instruction: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        session = self.repository.get_session(session_id)
        if session is None:
            raise RuntimeError("세션을 찾을 수 없습니다.")

        yield {"event": "session", "data": {"session_id": session.id, "run_id": run_id}}

        async for event in self._relay_agent_events(
            session_id=session.id,
            run_id=run_id,
            agent_stream=self.agent.astream_with_trace(
                session_id=str(session.id),
                run_id=run_id,
                resume={
                    "decision": decision,
                    "stage": stage,
                    "instruction": instruction or "",
                },
            ),
            append_assistant_message=True,
            session=session,
        ):
            yield event

    def get_pending_approval(
        self,
        *,
        session_id: int,
        run_id: str,
    ) -> PendingApprovalResponse | None:
        session = self.repository.get_session(session_id)
        if session is None:
            return None

        pending_approval = self.agent.get_pending_approval(run_id=run_id)
        if pending_approval is None:
            return None

        return PendingApprovalResponse(
            session_id=session.id,
            run_id=run_id,
            pending_approval=pending_approval,
        )

    async def _relay_agent_events(
        self,
        *,
        session_id: int,
        run_id: str,
        agent_stream: AsyncIterator[Dict[str, Any]],
        append_assistant_message: bool,
        session: Any,
    ) -> AsyncIterator[Dict[str, Any]]:
        answer_parts: list[str] = []
        thought_steps: list[Dict[str, Any]] = []
        preprocess_result: Dict[str, Any] | None = None
        visualization_result: Dict[str, Any] | None = None
        output_type: str | None = None

        async for event in agent_stream:
            event_type = event.get("type")
            if event_type == "thought":
                step = event.get("step")
                if isinstance(step, dict):
                    thought_steps.append(step)
                    yield {"event": "thought", "data": step}
            elif event_type == "approval_required":
                pending_approval = event.get("pending_approval")
                if isinstance(pending_approval, dict):
                    final_steps = event.get("thought_steps")
                    if isinstance(final_steps, list):
                        thought_steps = [step for step in final_steps if isinstance(step, dict)]
                    yield {
                        "event": "approval_required",
                        "data": {
                            "session_id": session_id,
                            "run_id": run_id,
                            "pending_approval": pending_approval,
                            "thought_steps": thought_steps,
                        },
                    }
                    return
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
                event_output_type = event.get("output_type")
                if isinstance(event_output_type, str) and event_output_type:
                    output_type = event_output_type

        final_answer = "".join(answer_parts).strip()
        if not final_answer:
            final_answer = "응답을 생성하지 못했습니다."

        if append_assistant_message:
            self.repository.append_message(session, "assistant", final_answer)
        done_data: Dict[str, Any] = {
            "answer": final_answer,
            "session_id": session_id,
            "run_id": run_id,
            "thought_steps": thought_steps,
            "preprocess_result": preprocess_result,
        }
        if isinstance(visualization_result, dict):
            done_data["visualization_result"] = visualization_result
        if output_type:
            done_data["output_type"] = output_type
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
