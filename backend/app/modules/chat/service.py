import uuid
from typing import Any, AsyncIterator, Dict, Optional

from ...core.trace_logging import log_trace, trace_context
from ...orchestration.client import AgentClient
from ..datasets.repository import DatasetRepository
from .models import ChatSession
from .repository import ChatRepository
from .schemas import ChatHistoryResponse, PendingApprovalResponse


class ChatService:
    """채팅 세션/실행 흐름을 함께 담당한다."""

    def __init__(
        self,
        *,
        agent: AgentClient,
        repository: ChatRepository,
        dataset_repository: DatasetRepository,
    ) -> None:
        self.agent = agent
        self.repository = repository
        self.dataset_repository = dataset_repository

    async def ask_stream(
        self,
        *,
        question: str,
        session_id: Optional[int] = None,
        model_id: Optional[str] = None,
        source_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        source_id = (source_id or "").strip() or None
        session = self._get_or_create_session(session_id=session_id, title=question)
        dataset = self.dataset_repository.get_by_source_id(source_id) if source_id else None

        run_id = uuid.uuid4().hex
        active_trace_id = (trace_id or "").strip() or uuid.uuid4().hex

        with trace_context(trace_id=active_trace_id, session_id=session.id, run_id=run_id):
            log_trace(
                layer="chat",
                event="ingress",
                payload={
                    "trace_id": active_trace_id,
                    "session_id": session.id,
                    "run_id": run_id,
                    "source_id": source_id,
                    "question": question,
                    "question_length": len(question),
                    "model_id": model_id,
                },
            )
            self.repository.append_message(session, "user", question)
            log_trace(
                layer="chat",
                event="user_message_saved",
                payload={
                    "role": "user",
                    "message_length": len(question),
                },
            )
            yield {
                "event": "session",
                "data": {
                    "session_id": session.id,
                    "run_id": run_id,
                    "trace_id": active_trace_id,
                },
            }

            async for event in self._relay_agent_events(
                session_id=session.id,
                run_id=run_id,
                trace_id=active_trace_id,
                agent_stream=self.agent.astream_with_trace(
                    session_id=str(session.id),
                    run_id=run_id,
                    question=question,
                    dataset=dataset,
                    model_id=model_id,
                ),
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
        trace_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        session = self._get_session(session_id)
        if session is None:
            raise RuntimeError("세션을 찾을 수 없습니다.")

        active_trace_id = (trace_id or "").strip() or run_id

        with trace_context(trace_id=active_trace_id, session_id=session.id, run_id=run_id):
            log_trace(
                layer="chat",
                event="resume_ingress",
                payload={
                    "trace_id": active_trace_id,
                    "session_id": session.id,
                    "run_id": run_id,
                    "decision": decision,
                    "stage": stage,
                    "instruction": instruction or "",
                },
            )
            yield {
                "event": "session",
                "data": {
                    "session_id": session.id,
                    "run_id": run_id,
                    "trace_id": active_trace_id,
                },
            }
            async for event in self._relay_agent_events(
                session_id=session.id,
                run_id=run_id,
                trace_id=active_trace_id,
                agent_stream=self.agent.astream_with_trace(
                    session_id=str(session.id),
                    run_id=run_id,
                    resume={
                        "decision": decision,
                        "stage": stage,
                        "instruction": instruction or "",
                    },
                ),
                session=session,
            ):
                yield event

    async def get_pending_approval(
        self,
        *,
        run_id: str,
    ) -> PendingApprovalResponse | None:
        pending_approval = await self.agent.get_pending_approval(run_id=run_id)
        if pending_approval is None:
            return None

        session_id = pending_approval.get("session_id")
        if not isinstance(session_id, int):
            return None

        return PendingApprovalResponse(
            session_id=session_id,
            run_id=run_id,
            pending_approval=pending_approval,
        )

    def has_session(self, session_id: int) -> bool:
        return self._get_session(session_id) is not None

    def has_dataset_source(self, source_id: str) -> bool:
        return self.dataset_repository.get_by_source_id(source_id) is not None

    def get_history(self, session_id: int) -> Optional[ChatHistoryResponse]:
        session = self._get_session(session_id)
        if not session:
            return None
        messages = self.repository.get_history(session_id)
        return ChatHistoryResponse(session_id=session_id, messages=messages)

    def delete_session(self, session_id: int) -> bool:
        return self.repository.delete_session(session_id)

    def _get_session(self, session_id: int) -> Optional[ChatSession]:
        return self.repository.get_session(session_id)

    def _get_or_create_session(self, *, session_id: int | None, title: str) -> ChatSession:
        session = self.repository.get_session(session_id) if session_id else None
        if session is None:
            session = self.repository.create_session(title=title[:60])
        return session

    @staticmethod
    def _extract_done_error_fields(
        *,
        report_result: Dict[str, Any] | None,
        preprocess_result: Dict[str, Any] | None,
        analysis_result: Dict[str, Any] | None,
        output_payload: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        error_stage = None
        error_message = None
        error_type = None

        if isinstance(report_result, dict) and report_result.get("status") == "failed":
            error_stage = "report"
            error_message = report_result.get("error") or report_result.get("summary")

        if isinstance(preprocess_result, dict) and preprocess_result.get("status") == "failed":
            error_stage = error_stage or "preprocess"
            error_message = error_message or preprocess_result.get("error") or preprocess_result.get("summary")

        if isinstance(analysis_result, dict):
            error_stage = error_stage or analysis_result.get("error_stage")
            error_message = error_message or analysis_result.get("error_message")

        if not error_message and isinstance(output_payload, dict):
            output_type = output_payload.get("type")
            output_content = output_payload.get("content")
            if isinstance(output_type, str) and output_type.endswith("_failed"):
                error_message = output_content

        return {
            "error_stage": error_stage,
            "error_message": error_message,
            "error_type": error_type,
        }

    async def _relay_agent_events(
        self,
        *,
        session_id: int,
        run_id: str,
        trace_id: str,
        agent_stream: AsyncIterator[Dict[str, Any]],
        session: ChatSession,
    ) -> AsyncIterator[Dict[str, Any]]:
        answer_parts: list[str] = []
        thought_steps: list[Dict[str, Any]] = []
        preprocess_result: Dict[str, Any] | None = None
        analysis_result: Dict[str, Any] | None = None
        visualization_result: Dict[str, Any] | None = None
        report_result: Dict[str, Any] | None = None
        output_type: str | None = None
        output_payload: Dict[str, Any] | None = None
        chunk_count = 0

        async for event in agent_stream:
            event_type = event.get("type")
            if event_type == "thought":
                step = event.get("step")
                if isinstance(step, dict):
                    thought_steps.append(step)
                    log_trace(
                        layer="chat",
                        event="thought",
                        payload={
                            "trace_id": trace_id,
                            "step": step,
                        },
                    )
                    yield {"event": "thought", "data": step}
            elif event_type == "approval_required":
                pending_approval = event.get("pending_approval")
                if isinstance(pending_approval, dict):
                    final_steps = event.get("thought_steps")
                    if isinstance(final_steps, list):
                        thought_steps = [step for step in final_steps if isinstance(step, dict)]
                    log_trace(
                        layer="chat",
                        event="approval_required",
                        payload={
                            "trace_id": trace_id,
                            "pending_stage": pending_approval.get("stage"),
                            "thought_step_count": len(thought_steps),
                        },
                    )
                    yield {
                        "event": "approval_required",
                        "data": {
                            "session_id": session_id,
                            "run_id": run_id,
                            "trace_id": trace_id,
                            "pending_approval": pending_approval,
                            "thought_steps": thought_steps,
                        },
                    }
                    return
            elif event_type == "chunk":
                delta = event.get("delta")
                if isinstance(delta, str) and delta:
                    answer_parts.append(delta)
                    chunk_count += 1
                    log_trace(
                        layer="chat",
                        event="chunk",
                        payload={
                            "trace_id": trace_id,
                            "chunk_count": chunk_count,
                            "accumulated_answer_length": len("".join(answer_parts)),
                            "last_delta_sample": delta,
                        },
                    )
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
                event_analysis = event.get("analysis_result")
                if isinstance(event_analysis, dict):
                    analysis_result = event_analysis
                event_visualization = event.get("visualization_result")
                if isinstance(event_visualization, dict):
                    visualization_result = event_visualization
                event_report = event.get("report_result")
                if isinstance(event_report, dict):
                    report_result = event_report
                event_output_type = event.get("output_type")
                if isinstance(event_output_type, str) and event_output_type:
                    output_type = event_output_type
                event_output = event.get("output")
                if isinstance(event_output, dict):
                    output_payload = event_output

        final_answer = "".join(answer_parts).strip()
        if not final_answer and isinstance(output_payload, dict):
            output_content = output_payload.get("content")
            if isinstance(output_content, str):
                final_answer = output_content.strip()
        if not final_answer:
            final_answer = "응답을 생성하지 못했습니다."

        self.repository.append_message(session, "assistant", final_answer)
        log_trace(
            layer="chat",
            event="assistant_message_saved",
            payload={
                "trace_id": trace_id,
                "role": "assistant",
                "message_length": len(final_answer),
            },
        )

        done_data: Dict[str, Any] = {
            "answer": final_answer,
            "session_id": session_id,
            "run_id": run_id,
            "trace_id": trace_id,
            "thought_steps": thought_steps,
            "preprocess_result": preprocess_result,
        }
        if isinstance(analysis_result, dict):
            done_data["analysis_result"] = analysis_result
        if isinstance(visualization_result, dict):
            done_data["visualization_result"] = visualization_result
        if isinstance(report_result, dict):
            done_data["report_result"] = report_result
        if output_type:
            done_data["output_type"] = output_type
        if isinstance(output_payload, dict):
            done_data["output"] = output_payload
        error_fields = self._extract_done_error_fields(
            report_result=report_result,
            preprocess_result=preprocess_result,
            analysis_result=analysis_result,
            output_payload=output_payload,
        )
        log_trace(
            layer="chat",
            event="done",
            payload={
                "trace_id": trace_id,
                "answer": final_answer,
                "output_type": output_type,
                "preprocess_status": (
                    preprocess_result.get("status") if isinstance(preprocess_result, dict) else None
                ),
                "analysis_execution_status": (
                    analysis_result.get("execution_status") if isinstance(analysis_result, dict) else None
                ),
                "visualization_status": (
                    visualization_result.get("status") if isinstance(visualization_result, dict) else None
                ),
                "report_status": (
                    report_result.get("status") if isinstance(report_result, dict) else None
                ),
                "pending_approval_stage": None,
                "error_stage": error_fields["error_stage"],
                "error_message": error_fields["error_message"],
                "error_type": error_fields["error_type"],
            },
        )
        yield {"event": "done", "data": done_data}
