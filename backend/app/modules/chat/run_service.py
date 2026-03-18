import uuid
from typing import Any, AsyncIterator, Dict, Optional

from ...orchestration.client import AgentClient
from ..datasets.repository import DataSourceRepository
from .models import ChatSession
from .repository import ChatRepository
from .schemas import PendingApprovalResponse
from .session_service import ChatSessionService


class ChatRunService:
    """run 생성, SSE relay, pending approval 조회를 담당한다."""

    def __init__(
        self,
        *,
        agent: AgentClient,
        repository: ChatRepository,
        session_service: ChatSessionService,
        data_source_repository: DataSourceRepository,
    ) -> None:
        self.agent = agent
        self.repository = repository
        self.session_service = session_service
        self.data_source_repository = data_source_repository

    async def ask_stream(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        model_id: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        session = self.session_service.get_or_create_session(session_id=session_id, title=question)
        dataset = self.data_source_repository.get_by_source_id(source_id) if source_id else None

        self.session_service.append_message(session=session, role="user", content=question)
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
        session = self.session_service.get_session(session_id)
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
        session = self.session_service.get_session(session_id)
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
        session: ChatSession,
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
            self.session_service.append_message(session=session, role="assistant", content=final_answer)

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
        yield {"event": "done", "data": done_data}
