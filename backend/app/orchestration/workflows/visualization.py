from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from backend.app.modules.visualization.executor import execute_visualization_plan
from backend.app.modules.visualization.planner import (
    VisualizationPlan,
    build_visualization_plan,
    build_visualization_review_payload,
    get_revision_instruction,
)
from backend.app.modules.visualization.service import VisualizationService
from backend.app.orchestration.state import VisualizationGraphState
from backend.app.orchestration.utils import resolve_target_source_id

MAX_SAMPLE_ROWS = 2000
MAX_POINTS = 120

logger = logging.getLogger(__name__)


def build_visualization_workflow(
    *,
    visualization_service: VisualizationService,
    default_model: str = "gpt-5-nano",
):
    def visualization_planner_node(state: VisualizationGraphState) -> Dict[str, Any]:
        analysis_result = state.get("analysis_result")
        analysis_plan = state.get("analysis_plan")
        source_id = resolve_target_source_id(state)
        logger.warning(
            "visualization_planner_node:start source_id=%r has_analysis_result=%r has_analysis_plan=%r",
            source_id,
            bool(analysis_result),
            bool(analysis_plan),
        )
        if analysis_result and analysis_plan:
            build_method = getattr(
                visualization_service, "build_from_analysis_result", None
            )
            if callable(build_method):
                visualization_result = build_method(
                    source_id=source_id or "",
                    analysis_plan=analysis_plan,
                    analysis_result=analysis_result,
                )
                logger.warning(
                    "visualization_planner_node:end status=%r summary=%r chart=%r",
                    visualization_result.get("status"),
                    visualization_result.get("summary"),
                    visualization_result.get("chart_data") or visualization_result.get("chart"),
                )
                return {
                    "visualization_plan": {
                        "status": "analysis_generated",
                        "source_id": source_id or "",
                    },
                    "visualization_result": visualization_result,
                }

        plan = build_visualization_plan(
            source_id=source_id,
            user_input=str(state.get("user_input", "")),
            revision_request=state.get("revision_request"),
            dataset_profile=state.get("dataset_profile"),
            model_id=state.get("model_id"),
            default_model=default_model,
            visualization_service=visualization_service,
            max_sample_rows=MAX_SAMPLE_ROWS,
        )
        logger.warning(
            "visualization_planner_node:end planned status=%r chart_type=%r x_key=%r y_key=%r",
            plan.status,
            plan.chart_type,
            plan.x_key,
            plan.y_key,
        )
        return {"visualization_plan": plan.model_dump()}

    def route_after_planner(state: VisualizationGraphState) -> str:
        plan_dict = state.get("visualization_plan") or {}
        if plan_dict.get("status") == "analysis_generated":
            return "done"
        if plan_dict.get("status") == "planned":
            return "approval"
        return "execute"

    def approval_gate_node(state: VisualizationGraphState) -> Dict[str, Any]:
        plan = VisualizationPlan.model_validate(state.get("visualization_plan") or {})
        source_id = str(plan.source_id or state.get("source_id") or "")
        preview_rows = visualization_service.build_preview_rows(
            source_id=source_id,
            x_key=plan.x_key,
            y_key=plan.y_key,
            limit=5,
        )
        payload = build_visualization_review_payload(
            source_id=source_id,
            plan=plan,
            preview_rows=preview_rows,
        )
        decision_raw = interrupt(payload)

        decision_value = ""
        instruction = ""
        if isinstance(decision_raw, dict):
            raw_decision = decision_raw.get("decision")
            raw_instruction = decision_raw.get("instruction")
            if isinstance(raw_decision, str):
                decision_value = raw_decision
            if isinstance(raw_instruction, str):
                instruction = raw_instruction.strip()
        elif isinstance(decision_raw, str):
            decision_value = decision_raw

        if decision_value == "approve":
            return {
                "approved_plan": plan.model_dump(),
                "pending_approval": {},
                "revision_request": {},
            }

        if decision_value == "revise":
            return {
                "approved_plan": {},
                "pending_approval": payload,
                "revision_request": {
                    "stage": "visualization",
                    "instruction": instruction,
                },
            }

        return {
            "approved_plan": {},
            "pending_approval": {},
            "revision_request": {},
            "visualization_result": {
                "status": "cancelled",
                "source_id": source_id,
                "summary": "시각화 계획 검토 단계에서 실행을 취소했습니다.",
            },
            "output": {
                "type": "cancelled",
                "content": "시각화 계획 검토 단계에서 실행을 취소했습니다.",
            },
        }

    def route_after_approval(state: VisualizationGraphState) -> str:
        result = state.get("visualization_result") or {}
        if result.get("status") == "cancelled":
            return "cancel"
        if get_revision_instruction(state.get("revision_request")):
            return "revise"
        return "approve"

    def visualization_executor_node(state: VisualizationGraphState) -> Dict[str, Any]:
        result = execute_visualization_plan(
            visualization_service=visualization_service,
            visualization_plan=state.get("visualization_plan"),
            approved_plan=state.get("approved_plan"),
            max_sample_rows=MAX_SAMPLE_ROWS,
            max_points=MAX_POINTS,
        )
        return {
            "visualization_result": result,
            "revision_request": {},
            "approved_plan": {},
            "pending_approval": {},
        }

    def cancel_node(_: VisualizationGraphState) -> Dict[str, Any]:
        return {}

    graph = StateGraph(VisualizationGraphState)
    graph.add_node("visualization_planner", visualization_planner_node)
    graph.add_node("approval_gate", approval_gate_node)
    graph.add_node("visualization_executor", visualization_executor_node)
    graph.add_node("cancel", cancel_node)
    graph.add_edge(START, "visualization_planner")
    graph.add_conditional_edges(
        "visualization_planner",
        route_after_planner,
        {
            "done": END,
            "approval": "approval_gate",
            "execute": "visualization_executor",
        },
    )
    graph.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "approve": "visualization_executor",
            "revise": "visualization_planner",
            "cancel": "cancel",
        },
    )
    graph.add_edge("visualization_executor", END)
    graph.add_edge("cancel", END)
    return graph.compile()
