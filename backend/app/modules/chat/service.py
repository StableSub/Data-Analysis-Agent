import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional, cast

from ...core.trace_logging import log_trace, trace_context
from ...orchestration.client import AgentClient
from ...orchestration.error_contract import sanitize_public_payload
from ..datasets.repository import DatasetRepository
from .models import ChatMessage, ChatSession
from .repository import ChatRepository
from .schemas import ChatHistoryResponse, ChatSessionListResponse, ChatSessionSummary, PendingApprovalResponse


def _datetime_min_utc() -> datetime:
    return datetime.min.replace(tzinfo=timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _preview(message: ChatMessage | None) -> str | None:
    if message is None:
        return None
    content = message.content.strip()
    if len(content) <= 80:
        return content
    return f"{content[:77]}..."


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
        guideline_source_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        source_id = (source_id or "").strip() or None
        if source_id is not None:
            dataset = self.dataset_repository.get_by_source_id(source_id)
            if dataset is None:
                session = self._get_session(session_id) if session_id else None
                run_id = uuid.uuid4().hex
                active_trace_id = (trace_id or "").strip() or uuid.uuid4().hex
                with trace_context(
                    trace_id=active_trace_id,
                    session_id=session_id if session is not None else None,
                    run_id=run_id,
                ):
                    event_data: Dict[str, Any] = {
                        "run_id": run_id,
                        "trace_id": active_trace_id,
                    }
                    if session is not None and session_id is not None:
                        event_data["session_id"] = session_id
                    log_trace(
                        layer="chat",
                        event="invalid_source_id",
                        payload={
                            "trace_id": active_trace_id,
                            "session_id": session_id if session is not None else None,
                            "run_id": run_id,
                            "source_id": source_id,
                        },
                    )
                    if session is not None:
                        yield {
                            "event": "session",
                            "data": event_data,
                        }
                    yield {
                        "event": "error",
                        "data": {
                            **event_data,
                            "status": "failed",
                            "stage": "dataset_resolution",
                            "error_stage": "dataset_resolution",
                            "error_message": "요청한 데이터셋을 찾을 수 없습니다.",
                            "error_code": "invalid_source_id",
                            "retryable": False,
                            "answer": "요청한 데이터셋을 찾을 수 없습니다.",
                            "message": "요청한 데이터셋을 찾을 수 없습니다.",
                            "thought_steps": [],
                        },
                    }
                return
        else:
            dataset = None

        session = self._get_or_create_session(session_id=session_id, title=question)
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
                    "guideline_source_id": guideline_source_id,
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
                    guideline_source_id=guideline_source_id,
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

    def list_sessions(self, skip: int = 0, limit: int = 20) -> ChatSessionListResponse:
        summaries = [self._summarize_session(session) for session in self.repository.list_sessions()]
        summaries.sort(key=lambda item: item.updated_at or _datetime_min_utc(), reverse=True)
        return ChatSessionListResponse(total=len(summaries), items=summaries[skip : skip + limit])

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
    def _summarize_session(session: ChatSession) -> ChatSessionSummary:
        messages = sorted(session.messages, key=lambda message: (message.created_at, message.id))
        last_message = messages[-1] if messages else None
        first_user_message = next((message for message in messages if message.role == "user"), None)
        updated_at = _as_utc(last_message.created_at) if last_message else None
        title = (session.title or "").strip() or _preview(first_user_message) or "새 채팅"
        return ChatSessionSummary(
            id=cast(int, session.id),
            title=title,
            updated_at=updated_at,
            last_message_preview=_preview(last_message),
            message_count=len(messages),
        )

    @staticmethod
    def _extract_done_error_fields(
        *,
        report_result: Dict[str, Any] | None,
        preprocess_result: Dict[str, Any] | None,
        analysis_result: Dict[str, Any] | None,
        visualization_result: Dict[str, Any] | None,
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

        if isinstance(visualization_result, dict) and visualization_result.get("status") == "failed":
            error_stage = error_stage or "visualization"
            error_message = error_message or visualization_result.get("error") or visualization_result.get("summary")

        if isinstance(analysis_result, dict):
            error_stage = error_stage or analysis_result.get("error_stage")
            error_message = error_message or analysis_result.get("error_message")

        if not error_message and isinstance(output_payload, dict):
            public_error = output_payload.get("public_error")
            if isinstance(public_error, dict):
                error_stage = error_stage or public_error.get("stage") or public_error.get("error_stage")
                error_message = public_error.get("message") or public_error.get("error_message")
            output_type = output_payload.get("type")
            output_content = output_payload.get("content")
            if isinstance(output_type, str) and output_type.endswith("_failed"):
                error_message = error_message or output_content

        return {
            "error_stage": error_stage,
            "error_message": error_message,
            "error_type": error_type,
        }

    @staticmethod
    def _derive_terminal_status(
        *,
        output_type: str | None,
        error_fields: Dict[str, Any],
        answer_quality: Dict[str, Any] | None,
    ) -> str:
        if output_type == "cancelled":
            return "cancelled"
        if output_type == "fail" or (isinstance(output_type, str) and output_type.endswith("_failed")):
            return "failed"
        if error_fields.get("error_stage") or error_fields.get("error_message"):
            return "failed"
        if isinstance(answer_quality, dict):
            quality_status = answer_quality.get("status")
            if quality_status in {"limited", "unanswerable"}:
                return str(quality_status)
        return "success"

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
        evidence_package: Dict[str, Any] | None = None
        answer_quality: Dict[str, Any] | None = None
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
                    output_evidence = event_output.get("evidence_package")
                    if isinstance(output_evidence, dict):
                        evidence_package = output_evidence
                    output_answer_quality = event_output.get("answer_quality")
                    if isinstance(output_answer_quality, dict):
                        answer_quality = output_answer_quality
                event_evidence = event.get("evidence_package")
                if isinstance(event_evidence, dict):
                    evidence_package = event_evidence
                event_quality = event.get("answer_quality")
                if isinstance(event_quality, dict):
                    answer_quality = event_quality

            elif event_type == "error":
                public_event = sanitize_public_payload(event)
                final_answer = event.get("answer") or "응답을 생성하지 못했습니다."
                if isinstance(public_event, dict):
                    final_answer = public_event.get("answer") or final_answer
                event_error_stage = event.get("error_stage") or event.get("stage") or "unknown"
                if isinstance(public_event, dict):
                    event_error_stage = public_event.get("error_stage") or public_event.get("stage") or event_error_stage
                event_error_message = event.get("error_message")
                if isinstance(public_event, dict):
                    event_error_message = public_event.get("error_message") or public_event.get("message") or event_error_message
                if not isinstance(event_error_message, str) or not event_error_message:
                    event_error_message = final_answer
                final_steps = event.get("thought_steps")
                if isinstance(final_steps, list):
                    thought_steps = [
                        step
                        for step in sanitize_public_payload(final_steps)
                        if isinstance(step, dict)
                    ]
                event_output = event.get("output")
                if isinstance(event_output, dict):
                    output_payload = sanitize_public_payload(event_output)
                    output_evidence = event_output.get("evidence_package")
                    if isinstance(output_evidence, dict):
                        evidence_package = sanitize_public_payload(output_evidence)
                    output_answer_quality = event_output.get("answer_quality")
                    if isinstance(output_answer_quality, dict):
                        answer_quality = sanitize_public_payload(output_answer_quality)
                event_evidence = event.get("evidence_package")
                if isinstance(event_evidence, dict):
                    evidence_package = sanitize_public_payload(event_evidence)
                event_quality = event.get("answer_quality")
                if isinstance(event_quality, dict):
                    answer_quality = sanitize_public_payload(event_quality)

                self.repository.append_message(session, "assistant", final_answer)
                log_trace(
                    layer="chat",
                    event="error",
                    payload={
                        "trace_id": trace_id,
                        "stage": event.get("stage"),
                        "status": event.get("status"),
                        "error_stage": event_error_stage,
                        "error_message": event_error_message,
                        "error_code": event.get("error_code"),
                        "retryable": event.get("retryable"),
                        "answer": final_answer,
                        "output_type": event.get("output_type"),
                    },
                )
                error_data: Dict[str, Any] = {
                    "session_id": session_id,
                    "run_id": run_id,
                    "trace_id": trace_id,
                    "thought_steps": thought_steps,
                    "answer": final_answer,
                    "message": final_answer,
                    # ── optional metadata ──
                    "status": event.get("status") or "failed",
                    "stage": event.get("stage") or event_error_stage,
                    "error_stage": event_error_stage,
                    "error_message": event_error_message,
                    "error_code": (
                        public_event.get("error_code")
                        if isinstance(public_event, dict)
                        else event.get("error_code")
                    ) or "unknown_error",
                    "retryable": bool(
                        public_event.get("retryable", False)
                        if isinstance(public_event, dict)
                        else event.get("retryable", False)
                    ),
                    "output_type": (
                        public_event.get("output_type")
                        if isinstance(public_event, dict)
                        else event.get("output_type")
                    ) or "",
                }
                public_error = (
                    public_event.get("public_error")
                    if isinstance(public_event, dict)
                    else event.get("public_error")
                )
                if isinstance(public_error, dict):
                    error_data["public_error"] = sanitize_public_payload(public_error)
                if isinstance(output_payload, dict):
                    error_data["output"] = output_payload
                if isinstance(evidence_package, dict):
                    error_data["evidence_package"] = evidence_package
                if isinstance(answer_quality, dict):
                    error_data["answer_quality"] = answer_quality
                yield {
                    "event": "error",
                    "data": sanitize_public_payload(
                        error_data,
                        fallback_message=event_error_message,
                    ),
                }
                return

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
        if isinstance(evidence_package, dict):
            done_data["evidence_package"] = evidence_package
        if isinstance(answer_quality, dict):
            done_data["answer_quality"] = answer_quality
        error_fields = self._extract_done_error_fields(
            report_result=report_result,
            preprocess_result=preprocess_result,
            analysis_result=analysis_result,
            visualization_result=visualization_result,
            output_payload=output_payload,
        )
        terminal_status = self._derive_terminal_status(
            output_type=output_type,
            error_fields=error_fields,
            answer_quality=answer_quality,
        )
        done_data["status"] = terminal_status
        if error_fields["error_stage"]:
            done_data["error_stage"] = error_fields["error_stage"]
        if error_fields["error_message"]:
            done_data["error_message"] = error_fields["error_message"]
        if error_fields["error_type"]:
            done_data["error_type"] = error_fields["error_type"]
        if terminal_status in {"failed", "cancelled"}:
            done_data["retryable"] = terminal_status == "failed"
        log_trace(
            layer="chat",
            event="done",
            payload={
                "trace_id": trace_id,
                "answer": final_answer,
                "output_type": output_type,
                "status": terminal_status,
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
