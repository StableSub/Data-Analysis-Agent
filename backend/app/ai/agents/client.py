"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, AsyncIterator, Dict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from ...core.db import SessionLocal
from .builder import build_main_workflow


def _load_pdf(file_path: Path, max_chars: int) -> str:
    """
    역할: PDF 파일에서 페이지별 텍스트를 읽어 지정 길이까지 누적 추출한다.
    입력: PDF 경로(`file_path`)와 최대 문자 수(`max_chars`)를 받는다.
    출력: 추출된 텍스트를 줄바꿈으로 합친 문자열을 반환하며, `pypdf` 미설치 시 예외를 발생시킨다.
    데코레이터: 없음.
    호출 맥락: `_load_text_from_file`에서 PDF 확장자를 처리할 때 내부 유틸로 호출된다.
    """
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF 파일을 처리하려면 'pypdf' 패키지가 필요합니다. pip install pypdf 로 설치하세요."
        ) from exc

    reader = PdfReader(str(file_path))
    chunks: list[str] = []
    total_len = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            available = max_chars - total_len
            if available <= 0:
                break
            snippet = text[:available]
            chunks.append(snippet)
            total_len += len(snippet)
        if total_len >= max_chars:
            break
    return "\n".join(chunks)


def _load_text_from_file(path: str, max_chars: int = 4000) -> str:
    """
    역할: 파일 확장자에 따라 텍스트 파일 또는 PDF를 읽고 안전한 미리보기 문자열을 만든다.
    입력: 파일 경로 문자열(`path`)과 최대 문자 수(`max_chars`)를 받는다.
    출력: 최대 길이로 잘린 텍스트를 반환하며, 파일이 없으면 `FileNotFoundError`를 발생시킨다.
    데코레이터: 없음.
    호출 맥락: 현재는 데이터셋/문서 미리보기 생성 시 재사용 가능한 공용 파일 로더로 유지된다.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _load_pdf(file_path, max_chars)

    data = file_path.read_text(encoding="utf-8", errors="ignore")
    return data[:max_chars]


class AgentClient:
    def __init__(
        self,
        model: str = "gpt-5-nano",
    ) -> None:
        """
        역할: 에이전트 클라이언트의 기본 모델, DB 세션, 메인 워크플로우를 초기화한다.
        입력: 기본 모델 식별자(`model`)를 받아 내부 상태(`default_model`)에 저장한다.
        출력: 반환값은 없고, 이후 스트리밍 요청을 처리할 준비된 인스턴스를 구성한다.
        데코레이터: 없음.
        호출 맥락: 의존성 주입(`get_agent`)에서 싱글턴으로 생성되어 API 요청에서 재사용된다.
        """
        self.default_model = model
        self._db = SessionLocal()
        self._checkpointer = InMemorySaver()
        self._workflow = build_main_workflow(
            db=self._db,
            default_model=self.default_model,
            checkpointer=self._checkpointer,
        )

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
        """
        역할: 워크플로우 실행 과정을 `thought/chunk/done` 이벤트 스트림으로 변환해 전달한다.
        입력: 세션/질문/컨텍스트/데이터셋/모델 식별자를 받아 초기 상태를 구성한다.
        출력: 비동기 이터레이터로 부분 응답과 최종 응답 이벤트 딕셔너리를 순차 반환한다.
        데코레이터: 없음.
        호출 맥락: 채팅/리포트 API 서비스 계층에서 SSE 응답을 만들 때 핵심 진입점으로 호출된다.
        """
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
        async for snapshot in self._astream_workflow_values(self._workflow, input_payload, config):
            final_state = snapshot
            pending_approval = self._extract_interrupt_payload(snapshot)
            if pending_approval is not None:
                pending_stage = str(pending_approval.get("stage") or "")
                approval_phase = "preprocess_approval"
                approval_message = "전처리 계획 승인을 기다리는 중입니다."
                if pending_stage == "visualization":
                    approval_phase = "visualization_approval"
                    approval_message = "시각화 계획 승인을 기다리는 중입니다."
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
        """
        역할: 사용자 요청을 LangGraph 입력 상태 포맷으로 정규화한다.
        입력: 세션, 질문, 컨텍스트, 데이터셋 객체, 모델 ID를 받아 상태 필드를 채운다.
        출력: `(state, early_answer)` 튜플을 반환하며, 질문이 비면 즉시 안내 문구를 반환한다.
        데코레이터: 없음.
        호출 맥락: `astream_with_trace` 시작 시 가장 먼저 호출되어 실행 전 유효 상태를 만든다.
        """
        _ = context
        question_text = (question or "").strip()
        if not question_text:
            return {}, "질문을 입력해 주세요."

        state: Dict[str, Any] = {
            "user_input": question_text,
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

    def get_pending_approval(self, *, run_id: str) -> Dict[str, Any] | None:
        snapshot = self._workflow.get_state(self._build_config(run_id=run_id, session_id=None))
        interrupts = getattr(snapshot, "interrupts", ())
        if not interrupts:
            return None
        pending_approval = getattr(interrupts[0], "value", None)
        return pending_approval if isinstance(pending_approval, dict) else None

    @staticmethod
    def _extract_answer(result_state: Dict[str, Any]) -> str:
        """
        역할: 최종 상태에서 사용자에게 보여줄 응답 본문 문자열을 추출한다.
        입력: 워크플로우 종료 상태 딕셔너리(`result_state`)를 받는다.
        출력: `output.content`가 있으면 해당 문자열, 없으면 기본 실패 메시지를 반환한다.
        데코레이터: @staticmethod. 인스턴스 속성 없이 입력 상태만으로 동작하는 정적 유틸이다.
        호출 맥락: 스트리밍 루프 종료 후 `done` 이벤트의 `answer` 값을 확정할 때 사용된다.
        """
        output = result_state.get("output")
        if isinstance(output, dict):
            content = output.get("content")
            if isinstance(content, str) and content:
                return content
        return "응답을 생성하지 못했습니다."

    @staticmethod
    def _make_step(*, phase: str, message: str, status: str = "completed") -> Dict[str, str]:
        """
        역할: 사용자 UI에 표시할 사고 단계(step) 레코드를 표준 구조로 생성한다.
        입력: 단계 구분(`phase`), 메시지(`message`), 상태(`status`)를 키워드 인자로 받는다.
        출력: `phase/message/status` 3개 키를 가진 딕셔너리를 반환한다.
        데코레이터: @staticmethod. 클래스/인스턴스 상태를 사용하지 않는 순수 생성 헬퍼다.
        호출 맥락: `_collect_thought_steps`와 초기 thought 이벤트 생성에서 공통으로 호출된다.
        """
        return {"phase": phase, "message": message, "status": status}

    @classmethod
    def _collect_thought_steps(cls, state: Dict[str, Any]) -> list[Dict[str, str]]:
        """
        역할: 그래프 상태 스냅샷을 사용자 친화적인 단계 목록으로 변환한다.
        입력: 노드 결과가 누적된 상태 딕셔너리(`state`)를 받아 단계 메시지를 조합한다.
        출력: UI 표시용 step 딕셔너리 리스트를 반환한다.
        데코레이터: @classmethod. `cls._make_step` 조합을 통해 클래스 단위 변환 규칙을 재사용한다.
        호출 맥락: `astream_with_trace`에서 새 스냅샷마다 thought 이벤트를 생성할 때 반복 호출된다.
        """
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
            retrieved_count = (
                retrieved_count_raw if isinstance(retrieved_count_raw, int) else 0
            )
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
        """
        역할: 워크플로우 실행 인터페이스(`astream` 또는 `invoke`)를 단일 비동기 스트림으로 추상화한다.
        입력: 컴파일된 워크플로우 객체(`workflow`)와 초기 상태(`state`)를 받는다.
        출력: 상태 스냅샷 딕셔너리를 비동기 이터레이터 형태로 순차 반환한다.
        데코레이터: @staticmethod. 인스턴스 필드에 의존하지 않고 입력 객체만으로 실행 경로를 결정한다.
        호출 맥락: `astream_with_trace` 내부에서 워크플로우 엔진 차이를 숨기기 위한 어댑터로 사용된다.
        """
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
