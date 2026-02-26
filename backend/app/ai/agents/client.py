"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator, Dict

from ...core.db import SessionLocal
from .builder import build_main_workflow


def _load_pdf(file_path: Path, max_chars: int) -> str:
    """
    간단한 PDF 텍스트 추출.
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
    텍스트 또는 PDF 파일을 읽어 제한 길이만큼 잘라 반환한다.
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
        self.default_model = model
        self._db = SessionLocal()
        self._workflow = build_main_workflow(
            db=self._db,
            default_model=self.default_model,
        )

    async def astream_with_trace(
        self,
        session_id: str | None = None,
        question: str | None = None,
        context: str | None = None,
        dataset: Any | None = None,
        model_id: str | None = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """비동기 스트리밍으로 답변과 사용자 표시용 사고 단계를 반환한다."""
        state, early_answer = self._build_state(
            session_id=session_id,
            question=question,
            context=context,
            dataset=dataset,
            model_id=model_id,
        )

        if early_answer is not None:
            yield {"type": "chunk", "delta": early_answer}
            yield {"type": "done", "answer": early_answer, "thought_steps": []}
            return

        seen: set[tuple[str, str]] = set()
        thought_steps: list[Dict[str, str]] = []

        initial_step = self._make_step(
            phase="analysis",
            message="요청을 분석하고 처리 경로를 결정하는 중입니다.",
            status="active",
        )
        seen.add((initial_step["phase"], initial_step["message"]))
        thought_steps.append(initial_step)
        yield {"type": "thought", "step": initial_step}

        final_state: Dict[str, Any] = {}
        async for snapshot in self._astream_workflow_values(self._workflow, state):
            final_state = snapshot
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
        question: str | None,
        context: str | None,
        dataset: Any | None,
        model_id: str | None,
    ) -> tuple[Dict[str, Any], str | None]:
        """워크플로우 입력 상태를 구성한다."""
        dataset_context = self._build_dataset_context(dataset) if dataset is not None else ""
        merged_context_parts: list[str] = []
        if dataset_context:
            merged_context_parts.append(dataset_context)
        if context:
            merged_context_parts.append(context)
        merged_context = "\n\n".join(merged_context_parts).strip()
        question_text = (question or "").strip()
        if not question_text:
            return {}, "질문을 입력해 주세요."

        if merged_context:
            message = f"{question_text}\n\ncontext:\n{merged_context}"
        else:
            message = question_text

        state: Dict[str, Any] = {
            "user_input": message,
            "session_id": str(session_id or ""),
            "model_id": model_id or self.default_model,
            "user_context": {"context": merged_context} if merged_context else {},
            "dataset_id": getattr(dataset, "id", None) if dataset is not None else None,
            "source_id": getattr(dataset, "source_id", None) if dataset is not None else None,
        }
        return state, None

    @staticmethod
    def _extract_answer(result_state: Dict[str, Any]) -> str:
        """워크플로우 상태에서 최종 답변 문자열을 추출한다."""
        output = result_state.get("output") or {}
        content = output.get("content")
        if isinstance(content, str) and content:
            return content

        preprocess_decision = result_state.get("preprocess_decision")
        if isinstance(preprocess_decision, dict):
            reason_summary = preprocess_decision.get("reason_summary")
            if isinstance(reason_summary, str) and reason_summary.strip():
                return reason_summary.strip()

        preprocess_plan = result_state.get("preprocess_plan")
        if isinstance(preprocess_plan, dict):
            planner_comment = preprocess_plan.get("planner_comment")
            if isinstance(planner_comment, str) and planner_comment.strip():
                return planner_comment.strip()

        preprocess_result = result_state.get("preprocess_result")
        if isinstance(preprocess_result, dict):
            status = preprocess_result.get("status")
            if status == "applied":
                applied_count = preprocess_result.get("applied_ops_count", 0)
                return f"전처리가 완료되었습니다. 적용한 연산 수: {applied_count}개."
            if status == "skipped":
                return "전처리 필요성이 낮아 전처리를 생략했습니다."
            if status == "failed":
                error_message = preprocess_result.get("error")
                if isinstance(error_message, str) and error_message.strip():
                    return f"전처리 단계에서 오류가 발생했습니다: {error_message.strip()}"

        if output:
            return str(output)
        return "응답을 생성하지 못했습니다."

    @staticmethod
    def _make_step(*, phase: str, message: str, status: str = "completed") -> Dict[str, str]:
        return {"phase": phase, "message": message, "status": status}

    @classmethod
    def _collect_thought_steps(cls, state: Dict[str, Any]) -> list[Dict[str, str]]:
        """워크플로우 상태를 사용자 표시용 단계 요약으로 변환한다."""
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
        state: Dict[str, Any],
    ) -> AsyncIterator[Dict[str, Any]]:
        """워크플로우 상태 스냅샷을 비동기 이터레이터로 제공한다."""
        if hasattr(workflow, "astream"):
            async for snapshot in workflow.astream(state, stream_mode="values"):
                if isinstance(snapshot, dict):
                    yield snapshot
            return

        final_state = await asyncio.to_thread(workflow.invoke, state)
        if isinstance(final_state, dict):
            yield final_state

    def _build_dataset_context(self, dataset: Any, max_rows: int = 20) -> str:
        """
        Dataset 객체에서 파일 내용을 읽어 LLM에 전달할 축약 컨텍스트를 만든다.
        """
        storage_path = getattr(dataset, "storage_path", None)
        filename = getattr(dataset, "filename", "dataset")
        if not storage_path:
            return ""

        file_path = Path(storage_path)
        if not file_path.exists() or not file_path.is_file():
            return ""

        try:
            if file_path.suffix.lower() == ".csv":
                import pandas as pd

                df = pd.read_csv(file_path, nrows=max_rows)
                preview_records = df.where(df.notnull(), None).to_dict(orient="records")
                return (
                    f"dataset filename={filename}\n"
                    f"columns={json.dumps(df.columns.tolist(), ensure_ascii=False)}\n"
                    f"preview_rows={json.dumps(preview_records, ensure_ascii=False)}"
                )

            raw_text = _load_text_from_file(str(file_path), max_chars=4000)
            return f"dataset filename={filename}\ncontent_preview={raw_text}"
        except Exception:
            return ""
