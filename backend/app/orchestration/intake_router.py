from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from .ai import analyze_intent
from .state import IntakeRouterState


def build_intake_router_workflow(
    *,
    default_model: str = "gpt-5-nano",
):
    def route_dataset_selected(state: IntakeRouterState) -> str:
        has_source_id = bool(str(state.get("source_id") or "").strip())
        return "data_selected" if has_source_id else "no_dataset"

    def general_question_node(_: IntakeRouterState) -> Dict[str, Any]:
        return {"handoff": {"next_step": "general_question"}}

    def analyze_intent_node(state: IntakeRouterState) -> Dict[str, Any]:
        decision = analyze_intent(
            user_input=str(state.get("user_input", "")),
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {"intent": decision.model_dump()}

    def data_pipeline_node(state: IntakeRouterState) -> Dict[str, Any]:
        intent = state.get("intent") or {}
        return {
            "handoff": {
                "next_step": "data_pipeline",
                "ask_preprocess": bool(intent.get("ask_preprocess", False)),
                "ask_visualization": bool(intent.get("ask_visualization", False)),
                "ask_report": bool(intent.get("ask_report", False)),
                "ask_guideline": bool(intent.get("ask_guideline", False)),
            }
        }

    graph = StateGraph(IntakeRouterState)
    graph.add_node("general_question_handoff", general_question_node)
    graph.add_node("analyze_intent", analyze_intent_node)
    graph.add_node("data_pipeline_handoff", data_pipeline_node)

    graph.add_conditional_edges(
        START,
        route_dataset_selected,
        {
            "no_dataset": "general_question_handoff",
            "data_selected": "analyze_intent",
        },
    )
    graph.add_edge("analyze_intent", "data_pipeline_handoff")
    graph.add_edge("general_question_handoff", END)
    graph.add_edge("data_pipeline_handoff", END)

    return graph.compile()
