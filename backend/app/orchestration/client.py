"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict

from langgraph.types import Command

from .presentation import build_approval_wait_step, collect_thought_steps, make_thought_step


class AgentClient:
    def __init__(
        self,
        *,
        workflow_runtime_factory: Any,
        checkpointer: Any,
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.default_model = default_model
        self._checkpointer = checkpointer
        self._workflow_runtime_factory = workflow_runtime_factory

    async def astream_with_trace(
        self,
        session_id: str | None = None,
        run_id: str | None = None,
        question: str | None = None,
        context: str | None = None,
        dataset: Any | None = None,
        model_id: str | None = None,
        resume: Dict[str, Any] | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        with self._runtime() as runtime:
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
                )
                seen.add((initial_step["phase"], initial_step["message"]))
                thought_steps.append(initial_step)
                yield {"type": "thought", "step": initial_step}

            final_state: Dict[str, Any] = {}
            async for snapshot in self._astream_workflow_values(workflow, input_payload, config):
                final_state = snapshot
                pending_approval = self._extract_interrupt_payload(snapshot)
                if pending_approval is not None:
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
            preprocess_result = final_state.get("preprocess_result")
            if isinstance(preprocess_result, dict):
                done_event["preprocess_result"] = preprocess_result
            visualization_result = final_state.get("visualization_result")
            if (
                isinstance(visualization_result, dict)
                and visualization_result.get("status") == "generated"
            ):
                done_event["visualization_result"] = visualization_result
            yield done_event

    def _runtime(self):
        return self._workflow_runtime_factory()

    def get_pending_approval(self, *, run_id: str) -> Dict[str, Any] | None:
        with self._runtime() as runtime:
            workflow = getattr(runtime, "workflow", runtime)
            snapshot = workflow.get_state(self._build_config(run_id=run_id, session_id=None))

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
    async def _astream_workflow_values(
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
