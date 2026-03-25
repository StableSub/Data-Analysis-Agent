"""
V1 리포트 서브그래프.

역할:
- 선택 데이터셋의 정량 지표와 인사이트/시각화를 반영한 리포트를 생성한다.
"""

from __future__ import annotations

from typing import Any, Dict

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
    def report_draft_node(state: ReportGraphState) -> Dict[str, Any]:
        target_source_id = resolve_target_source_id(state)

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

        draft = report_service.build_report_draft(
            question=question,
            source_id=str(target_source_id or ""),
            insight_summary=insight_summary,
            visualization_summary=visualization_summary,
            revision_instruction=revision_instruction,
            model_id=state.get("model_id"),
            visualizations=report_visualizations,
            default_model=default_model,
        )

        return {
            "report_draft": {**draft, "revision_count": revision_count},
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
