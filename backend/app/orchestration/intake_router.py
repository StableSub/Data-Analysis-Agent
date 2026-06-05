from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from ..modules.planner.service import PlannerService
from .guideline_routing import (
    has_selected_guideline,
    is_guideline_reference_question,
    is_selected_guideline_content_question,
)
from .state import IntakeRouterState


def build_intake_router_workflow(
    *,
    planner_service: PlannerService,
):
    def route_dataset_selected(state: IntakeRouterState) -> str:
        has_source_id = bool(str(state.get("source_id") or "").strip())
        if has_source_id:
            return "data_selected"
        user_input = str(state.get("user_input") or "")
        if is_guideline_reference_question(user_input) or (
            has_selected_guideline(state)
            and is_selected_guideline_content_question(user_input)
        ):
            return "guideline_selected"
        return "no_dataset"

    def general_question_node(state: IntakeRouterState) -> Dict[str, Any]:
        return {"handoff": {"next_step": "general_question"}}

    def dataset_selected_node(state: IntakeRouterState) -> Dict[str, Any]:
        return {"handoff": {"next_step": "dataset_selected"}}

    def guideline_selected_node(state: IntakeRouterState) -> Dict[str, Any]:
        return {"handoff": {"next_step": "guideline_selected"}}

    graph = StateGraph(IntakeRouterState)
    graph.add_node("general_question_handoff", general_question_node)
    graph.add_node("dataset_selected_handoff", dataset_selected_node)
    graph.add_node("guideline_selected_handoff", guideline_selected_node)

    graph.add_conditional_edges(
        START,
        route_dataset_selected,
        {
            "no_dataset": "general_question_handoff",
            "data_selected": "dataset_selected_handoff",
            "guideline_selected": "guideline_selected_handoff",
        },
    )
    graph.add_edge("dataset_selected_handoff", END)
    graph.add_edge("general_question_handoff", END)
    graph.add_edge("guideline_selected_handoff", END)

    return graph.compile()
