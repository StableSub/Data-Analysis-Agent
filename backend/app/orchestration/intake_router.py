from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from ..modules.planner.service import PlannerService
from .state import IntakeRouterState


def build_intake_router_workflow(
    *,
    planner_service: PlannerService,
):
    def route_dataset_selected(state: IntakeRouterState) -> str:
        has_source_id = bool(str(state.get("source_id") or "").strip())
        return "data_selected" if has_source_id else "no_dataset"

    def general_question_node(_: IntakeRouterState) -> Dict[str, Any]:
        return {"handoff": {"next_step": "general_question"}}

    def dataset_selected_node(_: IntakeRouterState) -> Dict[str, Any]:
        return {"handoff": {"next_step": "dataset_selected"}}

    graph = StateGraph(IntakeRouterState)
    graph.add_node("general_question_handoff", general_question_node)
    graph.add_node("dataset_selected_handoff", dataset_selected_node)

    graph.add_conditional_edges(
        START,
        route_dataset_selected,
        {
            "no_dataset": "general_question_handoff",
            "data_selected": "dataset_selected_handoff",
        },
    )
    graph.add_edge("dataset_selected_handoff", END)
    graph.add_edge("general_question_handoff", END)

    return graph.compile()
