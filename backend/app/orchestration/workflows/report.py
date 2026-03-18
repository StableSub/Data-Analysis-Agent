"""
V1 리포트 서브그래프.

역할:
- 선택 데이터셋의 정량 지표와 인사이트/시각화를 반영한 리포트를 생성한다.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.app.modules.reports.service import ReportService
from backend.app.orchestration.state import ReportGraphState
from backend.app.orchestration.utils import resolve_target_source_id


def _get_report_revision_instruction(state: ReportGraphState) -> str:
    revision_request = state.get("revision_request")
    if isinstance(revision_request, dict):
        if revision_request.get("stage") == "report":
            instruction = revision_request.get("instruction")
            if isinstance(instruction, str):
                return instruction.strip()
        return ""
    return str(revision_request or "").strip()


def build_report_workflow(*, report_service: ReportService, default_model: str = "gpt-5-nano"):
    """
    역할: 메트릭 계산과 LLM 리포트 작성을 담당하는 단일 노드 리포트 서브그래프를 생성한다.
    입력: DB 세션(`db`)과 리포트 작성 기본 모델명(`default_model`)을 받는다.
    출력: `report_result`와 `output(report_answer)`를 생성하는 컴파일된 그래프를 반환한다.
    데코레이터: 없음.
    호출 맥락: 메인 워크플로우에서 `ask_report`가 참일 때 최종 응답 경로로 호출된다.
    """
    def report_draft_node(state: ReportGraphState) -> Dict[str, Any]:
        """
        역할: 정량 메트릭, RAG 인사이트, 시각화 요약을 합쳐 리포트 초안을 생성한다.
        입력: `state.user_input`, `state.insight`, `state.visualization_result`, 대상 source 정보를 받는다.
        출력: `report_draft(summary/metrics/visualizations)`를 반환한다.
        데코레이터: 없음.
        호출 맥락: approval gate 직전에 실행되는 리포트 초안 생성 노드다.
        """
        target_source_id = resolve_target_source_id(state)

        metrics = report_service.build_metrics_for_source(str(target_source_id or ""))

        report_visualizations: list[Dict[str, Any]] = []

        insight = state.get("insight")
        insight_summary = ""
        if isinstance(insight, dict) and isinstance(insight.get("summary"), str):
            insight_summary = str(insight.get("summary")).strip()

        visualization_result = state.get("visualization_result")
        visualization_summary = ""
        if isinstance(visualization_result, dict):
            viz_summary = visualization_result.get("summary")
            if isinstance(viz_summary, str) and viz_summary.strip():
                visualization_summary = viz_summary.strip()
            if visualization_result.get("status") == "generated":
                chart = visualization_result.get("chart")
                artifact = visualization_result.get("artifact")
                if isinstance(chart, dict):
                    visualization_item: Dict[str, Any] = {"chart": chart}
                    if isinstance(artifact, dict):
                        visualization_item["artifact"] = artifact
                    report_visualizations.append(visualization_item)

        question = str(state.get("user_input", ""))
        revision_instruction = _get_report_revision_instruction(state)
        previous_draft = state.get("report_draft")
        revision_count = 0
        if isinstance(previous_draft, dict):
            revision_count = int(previous_draft.get("revision_count", 0) or 0)
        if revision_instruction:
            revision_count += 1
        model_name = state.get("model_id") or default_model
        llm = init_chat_model(model_name)
        result = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "당신은 데이터 분석 리포트 작성자다. "
                        "반드시 아래 3개 섹션 제목으로만 한국어 리포트를 작성하라.\n"
                        "요약\n핵심 인사이트\n권고사항\n"
                        "각 섹션은 2~5문장으로 작성하고, 가능한 한 수치를 인용하라. "
                        "단계 로그 설명은 금지한다."
                    )
                ),
                HumanMessage(
                    content=(
                        f"사용자 질문:\n{question}\n\n"
                        f"정량 지표(metrics):\n{json.dumps(metrics, ensure_ascii=False)}\n\n"
                        f"RAG 인사이트 요약:\n{insight_summary}\n\n"
                        f"시각화 요약:\n{visualization_summary}\n"
                        + (f"\n수정 요청:\n{revision_instruction}\n" if revision_instruction else "")
                    )
                ),
            ]
        )
        report_text = result.content if isinstance(result.content, str) else str(result.content)

        return {
            "report_draft": {
                "summary": report_text,
                "metrics": metrics,
                "visualizations": report_visualizations,
                "revision_count": revision_count,
            },
            "revision_request": {},
        }

    def approval_gate_node(state: ReportGraphState) -> Dict[str, Any]:
        draft = state.get("report_draft")
        if not isinstance(draft, dict):
            draft = {}

        payload = {
            "stage": "report",
            "kind": "draft_review",
            "title": "Report draft review",
            "summary": "리포트 초안을 검토한 뒤 승인, 수정 요청, 취소 중 하나를 선택해 주세요.",
            "source_id": str(resolve_target_source_id(state) or ""),
            "draft": str(draft.get("summary") or ""),
            "review": {
                "revision_count": int(draft.get("revision_count", 0) or 0),
            },
        }
        decision_raw = interrupt(payload)

        decision = ""
        instruction = ""
        if isinstance(decision_raw, dict):
            decision_value = decision_raw.get("decision")
            instruction_value = decision_raw.get("instruction")
            if isinstance(decision_value, str):
                decision = decision_value
            if isinstance(instruction_value, str):
                instruction = instruction_value.strip()
        elif isinstance(decision_raw, str):
            decision = decision_raw

        if decision == "approve":
            return {
                "pending_approval": {},
                "revision_request": {},
            }

        if decision == "revise":
            return {
                "pending_approval": payload,
                "revision_request": {
                    "stage": "report",
                    "instruction": instruction or "요청을 반영해 리포트 초안을 다시 작성해 주세요.",
                },
            }

        return {
            "pending_approval": {},
            "revision_request": {},
            "output": {
                "type": "cancelled",
                "content": "리포트 초안 검토 단계에서 실행을 취소했습니다.",
            },
        }

    def route_after_approval(state: ReportGraphState) -> str:
        output = state.get("output")
        if isinstance(output, dict) and output.get("type") == "cancelled":
            return "cancel"
        if _get_report_revision_instruction(state):
            return "revise"
        return "approve"

    def finalize_node(state: ReportGraphState) -> Dict[str, Any]:
        draft = state.get("report_draft")
        if not isinstance(draft, dict):
            draft = {}
        report_text = str(draft.get("summary") or "").strip()
        return {
            "report_result": draft,
            "pending_approval": {},
            "revision_request": {},
            "output": {
                "type": "report_answer",
                "content": report_text or "리포트 초안을 생성하지 못했습니다.",
            },
        }

    def cancel_node(_: ReportGraphState) -> Dict[str, Any]:
        return {
            "pending_approval": {},
            "revision_request": {},
        }

    graph = StateGraph(ReportGraphState)
    graph.add_node("report_draft", report_draft_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("cancel", cancel_node)
    graph.add_edge(START, "report_draft")
    graph.add_edge("report_draft", "approval_gate")
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "approve": "finalize",
            "revise": "report_draft",
            "cancel": "cancel",
        },
    )
    graph.add_edge("finalize", END)
    graph.add_edge("cancel", END)

    return graph.compile()


async def generate_report_summary(
    *,
    analysis_results: List[Dict[str, Any]],
    visualizations: List[Dict[str, Any]],
    insights: List[Any],
    service: ReportService,
) -> str:
    return await service.generate_summary(
        analysis_results=analysis_results,
        visualizations=visualizations,
        insights=insights,
    )
