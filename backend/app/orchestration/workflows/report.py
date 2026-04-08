"""
V1 리포트 서브그래프.

역할:
- 선택 데이터셋의 정량 지표와 인사이트/시각화를 반영한 리포트를 생성한다.
"""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.app.core.trace_logging import set_trace_stage
from backend.app.modules.reports.service import ReportService
from backend.app.orchestration.state import ReportGraphState
def _get_report_revision_instruction(state: ReportGraphState) -> str:
    revision_request = state.get("revision_request")
    if isinstance(revision_request, dict):
        if revision_request.get("stage") == "report":
            instruction = revision_request.get("instruction")
            if isinstance(instruction, str):
                return instruction.strip()
        return ""
    return str(revision_request or "").strip()


def _build_failed_report_payload(
    *,
    draft: Dict[str, Any] | None,
    error: str,
) -> Dict[str, Any]:
    draft_data = draft if isinstance(draft, dict) else {}
    return {
        "status": "failed",
        "summary": "리포트 생성에 실패했습니다.",
        "metrics": draft_data.get("metrics", {}),
        "visualizations": list(draft_data.get("visualizations") or []),
        "revision_count": int(draft_data.get("revision_count", 0) or 0),
        "error": error,
    }


def _build_failed_report_state(
    *,
    draft: Dict[str, Any] | None,
    error: str,
) -> Dict[str, Any]:
    failed = _build_failed_report_payload(draft=draft, error=error)
    return {
        "report_draft": failed,
        "report_result": failed,
        "final_status": "fail",
        "pending_approval": {},
        "revision_request": {},
        "output": {
            "type": "report_failed",
            "content": "리포트 생성에 실패했습니다.",
        },
    }


def build_report_workflow(*, report_service: ReportService, default_model: str = "gpt-5-nano"):
    def report_draft_node(state: ReportGraphState) -> Dict[str, Any]:
        set_trace_stage("report_draft")
        report_visualizations: list[Dict[str, Any]] = []

        visualization_result = state.get("visualization_result")
        if isinstance(visualization_result, dict):
            if visualization_result.get("status") == "generated":
                chart = visualization_result.get("chart_data")
                if not isinstance(chart, dict):
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

        try:
            draft = report_service.build_report_draft(
                question=question,
                analysis_result=state.get("analysis_result"),
                visualization_result=state.get("visualization_result"),
                guideline_context=state.get("guideline_context"),
                dataset_context=state.get("dataset_context"),
                revision_instruction=revision_instruction,
                model_id=state.get("model_id"),
                visualizations=report_visualizations,
                default_model=default_model,
            )
        except Exception as exc:
            failed = _build_failed_report_state(draft=None, error=str(exc))
            failed["report_draft"]["revision_count"] = revision_count
            failed["report_result"]["revision_count"] = revision_count
            return failed

        return {
            "report_draft": {**draft, "revision_count": revision_count},
            "revision_request": {},
        }

    def route_after_draft(state: ReportGraphState) -> str:
        draft = state.get("report_draft")
        if isinstance(draft, dict) and draft.get("status") == "failed":
            return "failed"
        return "approval"

    def approval_gate_node(state: ReportGraphState) -> Dict[str, Any]:
        set_trace_stage("report_approval")
        draft = state.get("report_draft")
        if not isinstance(draft, dict):
            draft = {}

        payload = {
            "stage": "report",
            "kind": "draft_review",
            "title": "Report draft review",
            "summary": "리포트 초안을 검토한 뒤 승인, 수정 요청, 취소 중 하나를 선택해 주세요.",
            "source_id": str((state.get("dataset_context") or {}).get("source_id") or state.get("source_id") or ""),
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
        set_trace_stage("report_finalize")
        draft = state.get("report_draft")
        if not isinstance(draft, dict):
            draft = {}
        report_text = str(draft.get("summary") or "").strip()
        if not report_text:
            return _build_failed_report_state(
                draft=draft,
                error="REPORT_DRAFT_EMPTY",
            )

        try:
            session_id = int(str(state.get("session_id") or "").strip())
            report = report_service.save_report(
                session_id=session_id,
                summary_text=report_text,
            )
        except Exception as exc:
            return _build_failed_report_state(draft=draft, error=str(exc))

        result = {
            **draft,
            "status": "generated",
            "report_id": report.id,
        }
        return {
            "report_result": result,
            "pending_approval": {},
            "revision_request": {},
            "output": {
                "type": "report_answer",
                "content": report_text or "리포트 초안을 생성하지 못했습니다.",
            },
        }

    def fail_node(_: ReportGraphState) -> Dict[str, Any]:
        return {
            "pending_approval": {},
            "revision_request": {},
        }

    def cancel_node(_: ReportGraphState) -> Dict[str, Any]:
        return {
            "pending_approval": {},
            "revision_request": {},
        }

    graph = StateGraph(ReportGraphState)
    graph.add_node("report_draft", report_draft_node)
    graph.add_node("fail", fail_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("finalize", finalize_node)
    graph.add_node("cancel", cancel_node)
    graph.add_edge(START, "report_draft")
    graph.add_conditional_edges(
        "report_draft",
        route_after_draft,
        {
            "approval": "approval_gate",
            "failed": "fail",
        },
    )
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "approve": "finalize",
            "revise": "report_draft",
            "cancel": "cancel",
        },
    )
    graph.add_edge("fail", END)
    graph.add_edge("finalize", END)
    graph.add_edge("cancel", END)

    return graph.compile()
