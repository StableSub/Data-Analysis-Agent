"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict

from langgraph.types import Command


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
                initial_step = self._make_step(
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
                    approval_phase = "preprocess_approval"
                    approval_message = "전처리 계획 승인을 기다리는 중입니다."
                    if pending_stage == "visualization":
                        approval_phase = "visualization_approval"
                        approval_message = "시각화 계획 승인을 기다리는 중입니다."
                    elif pending_stage == "report":
                        approval_phase = "report_approval"
                        approval_message = "리포트 초안 검토를 기다리는 중입니다."
                    approval_step = self._make_step(
                        phase=approval_phase,
                        message=approval_message,
                        status="active",
                    )
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
                for step in self._collect_thought_steps(snapshot):
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
        return pending_approval if isinstance(pending_approval, dict) else None

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
            "dataset_id": getattr(dataset, "id", None) if dataset is not None else None,
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
    def _make_step(*, phase: str, message: str, status: str = "completed") -> Dict[str, str]:
        return {"phase": phase, "message": message, "status": status}

    @classmethod
    def _collect_thought_steps(cls, state: Dict[str, Any]) -> list[Dict[str, str]]:
        steps: list[Dict[str, str]] = []

        handoff = state.get("handoff")
        if not isinstance(handoff, dict):
            handoff = {}
        else:
            next_step = handoff.get("next_step")
            if next_step == "data_pipeline":
                steps.append(
                    cls._make_step(
                        phase="intake",
                        message="데이터셋 기반 파이프라인으로 라우팅했습니다.",
                    )
                )
            elif next_step == "general_question":
                steps.append(
                    cls._make_step(
                        phase="intake",
                        message="일반 질의 경로로 라우팅했습니다.",
                    )
                )

            if bool(handoff.get("ask_visualization", False)):
                steps.append(
                    cls._make_step(
                        phase="intent",
                        message="시각화 요청이 감지되어 시각화 경로를 준비했습니다.",
                    )
                )
            if bool(handoff.get("ask_report", False)):
                steps.append(
                    cls._make_step(
                        phase="intent",
                        message="리포트 요청이 감지되어 리포트 경로를 준비했습니다.",
                    )
                )
            if bool(handoff.get("ask_preprocess", False)):
                steps.append(
                    cls._make_step(
                        phase="intent",
                        message="전처리 요청이 감지되어 전처리 단계를 준비했습니다.",
                    )
                )
            elif "ask_preprocess" in handoff:
                steps.append(
                    cls._make_step(
                        phase="intent",
                        message="전처리 요청이 없어 전처리 생략 경로를 준비했습니다.",
                    )
                )

        decision = state.get("preprocess_decision")
        if isinstance(decision, dict):
            reason_summary = decision.get("reason_summary")
            if isinstance(reason_summary, str) and reason_summary.strip():
                steps.append(
                    cls._make_step(
                        phase="preprocess_decision",
                        message=reason_summary.strip(),
                    )
                )
            else:
                decision_step = decision.get("step")
                if decision_step == "run_preprocess":
                    steps.append(
                        cls._make_step(
                            phase="preprocess_decision",
                            message="전처리가 필요하다고 판단했습니다.",
                        )
                    )
                elif decision_step == "skip_preprocess":
                    steps.append(
                        cls._make_step(
                            phase="preprocess_decision",
                            message="전처리를 생략해도 된다고 판단했습니다.",
                        )
                    )

        plan = state.get("preprocess_plan")
        if isinstance(plan, dict):
            planner_comment = plan.get("planner_comment")
            if isinstance(planner_comment, str) and planner_comment.strip():
                steps.append(
                    cls._make_step(
                        phase="preprocess_plan",
                        message=planner_comment.strip(),
                    )
                )
            else:
                operations = plan.get("operations")
                if isinstance(operations, list) and operations:
                    steps.append(
                        cls._make_step(
                            phase="preprocess_plan",
                            message=f"전처리 연산 {len(operations)}개를 계획했습니다.",
                        )
                    )

        result = state.get("preprocess_result")
        if isinstance(result, dict):
            status = result.get("status")
            if status == "applied":
                applied_count = result.get("applied_ops_count", 0)
                steps.append(
                    cls._make_step(
                        phase="preprocess_result",
                        message=f"전처리 연산 {applied_count}개를 적용했습니다.",
                    )
                )
            elif status == "skipped":
                steps.append(
                    cls._make_step(
                        phase="preprocess_result",
                        message="전처리 없이 다음 단계로 진행했습니다.",
                    )
                )
            elif status == "failed":
                error_message = result.get("error")
                if isinstance(error_message, str) and error_message.strip():
                    steps.append(
                        cls._make_step(
                            phase="preprocess_result",
                            message=f"전처리 단계에서 오류가 발생했습니다: {error_message.strip()}",
                            status="failed",
                        )
                    )
            elif status == "cancelled":
                steps.append(
                    cls._make_step(
                        phase="preprocess_result",
                        message="전처리 계획 검토 단계에서 실행을 취소했습니다.",
                    )
                )

        rag_index_status = state.get("rag_index_status")
        if isinstance(rag_index_status, dict):
            index_status = rag_index_status.get("status")
            source_id = rag_index_status.get("source_id")
            source_text = source_id if isinstance(source_id, str) and source_id else "-"
            if index_status == "created":
                steps.append(
                    cls._make_step(
                        phase="rag_index",
                        message=f"RAG 인덱스를 생성했습니다. (source_id={source_text})",
                    )
                )
            elif index_status == "existing":
                steps.append(
                    cls._make_step(
                        phase="rag_index",
                        message=f"기존 RAG 인덱스를 재사용합니다. (source_id={source_text})",
                    )
                )
            elif index_status == "dataset_missing":
                steps.append(
                    cls._make_step(
                        phase="rag_index",
                        message=f"RAG 인덱싱 대상 데이터셋을 찾지 못했습니다. (source_id={source_text})",
                        status="failed",
                    )
                )

        rag_result = state.get("rag_result")
        if isinstance(rag_result, dict):
            retrieved_count_raw = rag_result.get("retrieved_count")
            retrieved_count = retrieved_count_raw if isinstance(retrieved_count_raw, int) else 0
            source_id = rag_result.get("source_id")
            source_text = source_id if isinstance(source_id, str) and source_id else "-"
            if retrieved_count > 0:
                steps.append(
                    cls._make_step(
                        phase="rag_retrieval",
                        message=(
                            f"RAG 검색으로 관련 청크 {retrieved_count}개를 찾았습니다. "
                            f"(source_id={source_text})"
                        ),
                    )
                )
            else:
                steps.append(
                    cls._make_step(
                        phase="rag_retrieval",
                        message=(
                            f"RAG 검색에서 관련 청크를 찾지 못했습니다. "
                            f"(source_id={source_text})"
                        ),
                    )
                )

        insight = state.get("insight")
        if isinstance(insight, dict):
            insight_summary = insight.get("summary")
            if isinstance(insight_summary, str) and insight_summary.strip():
                steps.append(
                    cls._make_step(
                        phase="insight",
                        message=insight_summary.strip(),
                    )
                )

        visualization_result = state.get("visualization_result")
        if isinstance(visualization_result, dict):
            viz_summary = visualization_result.get("summary")
            viz_status = visualization_result.get("status")
            if isinstance(viz_summary, str) and viz_summary.strip():
                steps.append(
                    cls._make_step(
                        phase="visualization",
                        message=viz_summary.strip(),
                    )
                )
            elif viz_status == "generated":
                steps.append(
                    cls._make_step(
                        phase="visualization",
                        message="시각화 결과를 생성했습니다.",
                    )
                )

        merged_context = state.get("merged_context")
        if isinstance(merged_context, dict):
            applied_steps = merged_context.get("applied_steps")
            if isinstance(applied_steps, list):
                steps.append(
                    cls._make_step(
                        phase="merge_context",
                        message=f"누적 컨텍스트를 병합했습니다. (steps={len(applied_steps)})",
                    )
                )

        report_draft = state.get("report_draft")
        if isinstance(report_draft, dict):
            report_summary = report_draft.get("summary")
            if isinstance(report_summary, str) and report_summary.strip():
                revision_count = int(report_draft.get("revision_count", 0) or 0)
                steps.append(
                    cls._make_step(
                        phase="report_draft",
                        message=(
                            "수정 요청을 반영해 리포트 초안을 다시 작성했습니다."
                            if revision_count > 0
                            else "리포트 초안을 작성했습니다."
                        ),
                    )
                )

        report_result = state.get("report_result")
        if isinstance(report_result, dict):
            report_summary = report_result.get("summary")
            if isinstance(report_summary, str) and report_summary.strip():
                steps.append(
                    cls._make_step(
                        phase="report",
                        message="리포트 응답을 구성했습니다.",
                    )
                )

        revision_request = state.get("revision_request")
        if isinstance(revision_request, dict) and revision_request.get("stage") == "report":
            instruction = revision_request.get("instruction")
            if isinstance(instruction, str) and instruction.strip():
                steps.append(
                    cls._make_step(
                        phase="report_revision",
                        message=f"리포트 수정 요청을 반영합니다: {instruction.strip()}",
                    )
                )

        data_qa_result = state.get("data_qa_result")
        if isinstance(data_qa_result, dict):
            content = data_qa_result.get("content")
            if isinstance(content, str) and content.strip():
                steps.append(
                    cls._make_step(
                        phase="data_qa",
                        message="데이터 QA 응답을 구성했습니다.",
                    )
                )

        output = state.get("output")
        if not isinstance(output, dict):
            return steps
        output_type = output.get("type")
        if isinstance(output_type, str) and output_type.strip():
            steps.append(
                cls._make_step(
                    phase="output",
                    message=f"{output_type} 응답을 구성하고 있습니다.",
                )
            )
        return steps

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
