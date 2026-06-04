"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict

from langgraph.types import Command

from ..core.trace_logging import log_trace
from .error_contract import (
    build_failure_output,
    public_message_for_stage,
    sanitize_public_message,
    sanitize_public_payload,
    to_public_error,
)
from .state_view import build_approval_wait_step, collect_thought_steps, make_thought_step


class AgentClient:
    def __init__(
        self,
        *,
        workflow_runtime_factory: Any,
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.default_model = default_model
        self._workflow_runtime_factory = workflow_runtime_factory

    async def astream_with_trace(
        self,
        session_id: str | None = None,
        run_id: str | None = None,
        question: str | None = None,
        context: str | None = None,
        dataset: Any | None = None,
        model_id: str | None = None,
        guideline_source_id: str | None = None,
        resume: Dict[str, Any] | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        async with self._runtime() as runtime:
            workflow = getattr(runtime, "workflow", runtime)
            config = self._build_config(run_id=run_id, session_id=session_id)
            if resume is None:
                state, early_answer = self._build_state(
                    session_id=session_id,
                    run_id=run_id,
                    question=question,
                    context=context,
                    dataset=dataset,
                    model_id=model_id,
                    guideline_source_id=guideline_source_id,
                )
                if early_answer is not None:
                    yield {"type": "chunk", "delta": early_answer}
                    yield {"type": "done", "answer": early_answer, "thought_steps": []}
                    return
                input_payload: Any = state
            else:
                input_payload = Command(resume=resume)

            seen: set[tuple[str, str]] = set()
            thought_steps: list[Dict[str, str]] = []

            if resume is None:
                initial_step = make_thought_step(
                    phase="analysis",
                    message="요청을 분석하고 처리 경로를 결정하는 중입니다.",
                    status="active",
                    display_message="질문을 이해하고 있습니다.",
                )
                seen.add((initial_step["phase"], initial_step["message"]))
                thought_steps.append(initial_step)
                yield {"type": "thought", "step": initial_step}

            final_state: Dict[str, Any] = {}
            async for snapshot in self._astream_workflow_values(workflow, input_payload, config):
                final_state = snapshot
                log_trace(
                    layer="workflow",
                    event="snapshot",
                    payload=self._summarize_snapshot(snapshot),
                )
                pending_approval = self._extract_interrupt_payload(snapshot)
                if pending_approval is not None:
                    log_trace(
                        layer="workflow",
                        event="workflow_interrupt",
                        payload={
                            "stage": pending_approval.get("stage"),
                            "kind": pending_approval.get("kind"),
                        },
                    )
                    pending_stage = str(pending_approval.get("stage") or "")
                    approval_step = build_approval_wait_step(pending_stage)
                    key = (approval_step["phase"], approval_step["message"])
                    if key not in seen:
                        seen.add(key)
                        thought_steps.append(approval_step)
                        yield {"type": "thought", "step": approval_step}
                    yield {
                        "type": "approval_required",
                        "pending_approval": pending_approval,
                        "thought_steps": thought_steps,
                    }
                    return
                for step in collect_thought_steps(snapshot):
                    key = (step["phase"], step["message"])
                    if key in seen:
                        continue
                    seen.add(key)
                    thought_steps.append(step)
                    yield {"type": "thought", "step": step}

            log_trace(
                layer="workflow",
                event="workflow_final_state",
                payload=self._summarize_snapshot(final_state),
            )

            # 실패 분기: error event 전송 후 종료 
            if self._is_failed_state(final_state):
                summary = self._summarize_snapshot(final_state)
                workflow_error = final_state.get("workflow_error")
                public_error = to_public_error(workflow_error if isinstance(workflow_error, dict) else None)
                has_workflow_error = isinstance(workflow_error, dict)
                error_stage = public_error["stage"] if has_workflow_error else summary.get("error_stage") or "unknown"
                fallback_message = public_error["message"] if has_workflow_error else public_message_for_stage(str(error_stage))
                error_message = (
                    public_error["message"]
                    if has_workflow_error
                    else sanitize_public_message(
                        str(summary.get("error_message") or ""),
                        fallback_message=fallback_message,
                    )
                )
                answer = (
                    public_error["message"]
                    if has_workflow_error
                    else sanitize_public_message(
                        self._extract_answer(final_state),
                        fallback_message=fallback_message,
                    )
                )
                output_payload = (
                    build_failure_output(workflow_error)
                    if has_workflow_error
                    else final_state.get("output")
                )
                thought_steps = [
                    step
                    for step in sanitize_public_payload(
                        thought_steps,
                        fallback_message=fallback_message,
                    )
                    if isinstance(step, dict)
                ]
                error_event: Dict[str, Any] = {
                    "type": "error",
                    "status": "failed",
                    "stage": error_stage,
                    "error_stage": error_stage,
                    "error_message": error_message if isinstance(error_message, str) else answer,
                    "error_code": public_error["error_code"] if has_workflow_error else self._resolve_error_code(final_state, summary),
                    "retryable": public_error["retryable"] if has_workflow_error else self._resolve_retryable(final_state, summary),
                    "answer": answer,
                    "thought_steps": thought_steps,
                    "output_type": public_error["output_type"] if has_workflow_error else self._extract_output_type(final_state),
                }
                if has_workflow_error:
                    error_event["message"] = public_error["message"]
                    error_event["public_error"] = public_error
                if isinstance(output_payload, dict):
                    error_event["output"] = sanitize_public_payload(
                        output_payload,
                        fallback_message=fallback_message,
                    )
                evidence_package = final_state.get("evidence_package")
                if isinstance(evidence_package, dict):
                    error_event["evidence_package"] = sanitize_public_payload(evidence_package)
                answer_quality = final_state.get("answer_quality")
                if isinstance(answer_quality, dict):
                    error_event["answer_quality"] = sanitize_public_payload(answer_quality)
                yield sanitize_public_payload(
                    error_event,
                    fallback_message=fallback_message,
                )
                return
            
            # 정상 완료 분기 : done event 전송
            answer = self._extract_answer(final_state)
            for index in range(0, len(answer), 24):
                delta = answer[index:index + 24]
                yield {"type": "chunk", "delta": delta}
                await asyncio.sleep(0)
            done_event: Dict[str, Any] = {
                "type": "done",
                "answer": answer,
                "thought_steps": thought_steps,
                "output_type": self._extract_output_type(final_state),
            }
            output = final_state.get("output")
            if isinstance(output, dict):
                done_event["output"] = output

            # optional metadata
            evidence_package = final_state.get("evidence_package")
            if isinstance(evidence_package, dict):
                done_event["evidence_package"] = evidence_package
 
            # answer_quality: answerable / status / abstain_reason / warnings
            answer_quality = final_state.get("answer_quality")
            if isinstance(answer_quality, dict):
                done_event["answer_quality"] = answer_quality

            preprocess_result = final_state.get("preprocess_result")
            if isinstance(preprocess_result, dict):
                done_event["preprocess_result"] = preprocess_result
            analysis_result = final_state.get("analysis_result")
            if isinstance(analysis_result, dict):
                done_event["analysis_result"] = analysis_result
            visualization_result = final_state.get("visualization_result")
            if (
                isinstance(visualization_result, dict)
                and visualization_result.get("status") == "generated"
            ):
                done_event["visualization_result"] = visualization_result
            report_result = final_state.get("report_result")
            if isinstance(report_result, dict):
                done_event["report_result"] = report_result
            yield done_event

    def _runtime(self):
        return self._workflow_runtime_factory()

    async def get_pending_approval(self, *, run_id: str) -> Dict[str, Any] | None:
        async with self._runtime() as runtime:
            workflow = getattr(runtime, "workflow", runtime)
            snapshot = await workflow.aget_state(
                self._build_config(run_id=run_id, session_id=None)
            )

        interrupts = getattr(snapshot, "interrupts", ())
        if not interrupts:
            return None
        pending_approval = getattr(interrupts[0], "value", None)
        if not isinstance(pending_approval, dict):
            return None

        values = getattr(snapshot, "values", None)
        if isinstance(values, dict):
            session_id = values.get("session_id")
            if isinstance(session_id, int):
                pending_approval = {
                    **pending_approval,
                    "session_id": session_id,
                }
            elif isinstance(session_id, str) and session_id.strip().isdigit():
                pending_approval = {
                    **pending_approval,
                    "session_id": int(session_id),
                }

        return pending_approval

    def _build_state(
        self,
        *,
        session_id: str | None,
        run_id: str | None,
        question: str | None,
        context: str | None,
        dataset: Any | None,
        model_id: str | None,
        guideline_source_id: str | None,
    ) -> tuple[Dict[str, Any], str | None]:
        question_text = (question or "").strip()
        context_text = (context or "").strip()
        if not question_text:
            return {}, "질문을 입력해 주세요."

        state: Dict[str, Any] = {
            "user_input": question_text,
            "request_context": context_text,
            "session_id": str(session_id or ""),
            "run_id": str(run_id or ""),
            "model_id": model_id or self.default_model,
            "active_guideline_source_id": (guideline_source_id or "").strip(),
            # source_id is the dataset this run should actively use.
            "source_id": getattr(dataset, "source_id", None) if dataset is not None else None,
        }
        return state, None

    @staticmethod
    def _build_config(*, run_id: str | None, session_id: str | None) -> Dict[str, Any]:
        thread_id = str(run_id or session_id or "default")
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _extract_output_type(result_state: Dict[str, Any]) -> str:
        output = result_state.get("output")
        if isinstance(output, dict):
            output_type = output.get("type")
            if isinstance(output_type, str):
                return output_type
        return ""

    @staticmethod
    def _extract_interrupt_payload(snapshot: Dict[str, Any]) -> Dict[str, Any] | None:
        interrupts = snapshot.get("__interrupt__")
        if not isinstance(interrupts, tuple) or not interrupts:
            return None
        interrupt = interrupts[0]
        value = getattr(interrupt, "value", None)
        return value if isinstance(value, dict) else None

    @staticmethod
    def _extract_answer(result_state: Dict[str, Any]) -> str:
        output = result_state.get("output")
        if isinstance(output, dict):
            content = output.get("content")
            if isinstance(content, str) and content:
                return content

        return "응답을 생성하지 못했습니다."

    @staticmethod
    def _is_failed_state(state: Dict[str, Any]) -> bool:
        """workflow 최종 상태가 실패인지 판단한다."""
        if state.get("final_status") == "fail":
            return True
        output = state.get("output")
        if isinstance(output, dict):
            output_type = output.get("type", "")
            # preprocess_failed, planning_failed, cancelled 등 실패 계열 type
            if isinstance(output_type, str) and output_type.endswith("failed"):
                return True
        analysis_result = state.get("analysis_result")
        if isinstance(analysis_result, dict):
            if analysis_result.get("execution_status") == "fail":
                return True
            if analysis_result.get("quality_status") in ("empty", "invalid"):
                return True
        report_result = state.get("report_result")
        if isinstance(report_result, dict) and report_result.get("status") == "failed":
            return True
        return False
 
    @staticmethod
    def _resolve_error_code(state: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """실패 원인을 machine-readable error_code 로 변환한다."""
        workflow_error = state.get("workflow_error")
        if isinstance(workflow_error, dict) and isinstance(workflow_error.get("error_code"), str):
            return str(workflow_error["error_code"])
        output = state.get("output") or {}
        output_type = str(output.get("type") or "")
 
        if output_type == "planning_failed":
            return "planning_failed"
        if output_type == "preprocess_failed":
            return "preprocess_failed"
 
        analysis_result = state.get("analysis_result") or {}
        if analysis_result.get("execution_status") == "fail":
            error_stage = summary.get("error_stage") or ""
            if error_stage in ("code_validation", "result_validation"):
                return "analysis_validation_failed"
            return "analysis_execution_failed"

        quality_status = analysis_result.get("quality_status")
        if quality_status == "empty":
            return "analysis_empty_result"   # 재시도 가능
        if quality_status == "invalid":
            return "analysis_validation_failed"  # 재시도 불가
    
        report_result = state.get("report_result") or {}
        if report_result.get("status") == "failed":
            return "report_failed"
 
        answer_quality = state.get("answer_quality") or {}
        if answer_quality.get("answerable") is False:
            return "answer_unanswerable"
 
        return "unknown_error"
    
    @staticmethod
    def _resolve_retryable(state: Dict[str, Any], summary: Dict[str, Any]) -> bool:
        """해당 오류가 클라이언트 재시도로 복구 가능한지 판단한다."""
        workflow_error = state.get("workflow_error")
        if isinstance(workflow_error, dict) and "retryable" in workflow_error:
            return bool(workflow_error.get("retryable", False))
        error_code = AgentClient._resolve_error_code(state, summary)
        return error_code in ("planning_failed", "analysis_execution_failed", "analysis_empty_result", "unknown_error",)
 
    @staticmethod
    def _summarize_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
        handoff = snapshot.get("handoff")
        planning_result = snapshot.get("planning_result")
        output = snapshot.get("output")
        analysis_result = snapshot.get("analysis_result")
        analysis_error = snapshot.get("analysis_error")
        sandbox_result = snapshot.get("sandbox_result")
        visualization_result = snapshot.get("visualization_result")
        report_result = snapshot.get("report_result")
        interrupt = AgentClient._extract_interrupt_payload(snapshot)
        error_stage = None
        error_message = None
        error_type = None
        workflow_error = snapshot.get("workflow_error")

        if isinstance(workflow_error, dict):
            public_error = to_public_error(workflow_error)
            error_stage = public_error["stage"]
            error_message = public_error["message"]
            details = workflow_error.get("details")
            if isinstance(details, dict):
                error_type = details.get("exception_type") or details.get("error_type")

        if not error_stage and isinstance(analysis_error, dict):
            error_stage = analysis_error.get("stage")
        if not error_message and isinstance(analysis_error, dict):
            error_message = analysis_error.get("message")
        if isinstance(analysis_error, dict):
            detail = analysis_error.get("detail")
            if isinstance(detail, dict):
                error_type = detail.get("exception_type") or detail.get("error_type")

        if not error_stage and isinstance(analysis_result, dict):
            error_stage = analysis_result.get("error_stage")
        if not error_message and isinstance(analysis_result, dict):
            error_message = analysis_result.get("error_message")
        if (
            not error_stage
            and isinstance(report_result, dict)
            and report_result.get("status") == "failed"
        ):
            error_stage = "report"
        if (
            not error_message
            and isinstance(report_result, dict)
            and report_result.get("status") == "failed"
        ):
            error_message = report_result.get("error") or report_result.get("summary")
        if not error_type and isinstance(sandbox_result, dict):
            error_type = sandbox_result.get("error_type")
        is_failed_snapshot = (
            snapshot.get("final_status") == "fail"
            or (
                isinstance(analysis_result, dict)
                and analysis_result.get("execution_status") == "fail"
            )
            or (
                isinstance(report_result, dict)
                and report_result.get("status") == "failed"
            )
        )
        if is_failed_snapshot and not error_message and isinstance(output, dict):
            output_content = output.get("content")
            if isinstance(output_content, str) and output_content:
                error_message = output_content

        return {
            "handoff_next_step": (
                handoff.get("next_step") if isinstance(handoff, dict) else None
            ),
            "planning_route": (
                planning_result.get("route") if isinstance(planning_result, dict) else None
            ),
            "planning_preprocess_required": (
                planning_result.get("preprocess_required")
                if isinstance(planning_result, dict)
                else None
            ),
            "planning_need_visualization": (
                planning_result.get("need_visualization")
                if isinstance(planning_result, dict)
                else None
            ),
            "planning_need_report": (
                planning_result.get("need_report")
                if isinstance(planning_result, dict)
                else None
            ),
            "final_status": snapshot.get("final_status"),
            "output_type": output.get("type") if isinstance(output, dict) else None,
            "analysis_execution_status": (
                analysis_result.get("execution_status")
                if isinstance(analysis_result, dict)
                else None
            ),
            "visualization_status": (
                visualization_result.get("status")
                if isinstance(visualization_result, dict)
                else None
            ),
            "report_status": (
                report_result.get("status")
                if isinstance(report_result, dict)
                else None
            ),
            "error_stage": error_stage,
            "error_message": error_message,
            "error_type": error_type,
            "interrupt_stage": interrupt.get("stage") if isinstance(interrupt, dict) else None,
        }

    async def _astream_workflow_values(
        self,
        workflow: Any,
        input_payload: Any,
        config: Dict[str, Any],
    ) -> AsyncIterator[Dict[str, Any]]:
        if hasattr(workflow, "astream"):
            async for snapshot in workflow.astream(input_payload, config, stream_mode="values"):
                if isinstance(snapshot, dict):
                    yield snapshot
            return

        final_state = await asyncio.to_thread(
            workflow.invoke,
            input_payload,
            config,
            stream_mode="values",
        )
        if isinstance(final_state, dict):
            yield final_state
