from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from .ai import answer_data_question, answer_general_question
from .intake_router import build_intake_router_workflow
from .state import MainWorkflowState
from .workflows.preprocess import build_preprocess_workflow
from .workflows.rag import build_rag_workflow
from .workflows.report import build_report_workflow
from .workflows.visualization import build_visualization_workflow


def build_main_workflow(
    *,
    preprocess_service,
    rag_service,
    visualization_service,
    report_service,
    default_model: str = "gpt-5-nano",
    checkpointer: Any | None = None,
):
    intake_graph = build_intake_router_workflow(default_model=default_model)
    preprocess_graph = build_preprocess_workflow(
        preprocess_service=preprocess_service,
        default_model=default_model,
    )
    rag_graph = build_rag_workflow(
        rag_service=rag_service,
        default_model=default_model,
    )
    visualization_graph = build_visualization_workflow(
        visualization_service=visualization_service,
        default_model=default_model,
    )
    report_graph = build_report_workflow(
        report_service=report_service,
        default_model=default_model,
    )

    def route_after_intake(state: MainWorkflowState) -> str:
        branch = str((state.get("handoff") or {}).get("next_step", "general_question"))
        return branch

    def route_after_rag(state: MainWorkflowState) -> str:
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "merge_context"

    def route_after_preprocess(state: MainWorkflowState) -> str:
        preprocess_result = state.get("preprocess_result") or {}
        output = state.get("output") or {}
        if preprocess_result.get("status") == "cancelled" or output.get("type") == "cancelled":
            return "cancelled"
        return "rag"

    def route_after_merge_context(state: MainWorkflowState) -> str:
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_report", False)):
            return "report"
        return "data_qa"

    def route_after_visualization(state: MainWorkflowState) -> str:
        visualization_result = state.get("visualization_result") or {}
        output = state.get("output") or {}
        if visualization_result.get("status") == "cancelled" or output.get("type") == "cancelled":
            return "cancelled"
        return "merge_context"

    def general_question_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        answer = answer_general_question(
            user_input=str(state.get("user_input", "")),
            request_context=str(state.get("request_context", "")),
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {
            "output": {
                "type": "general_question",
                "content": answer,
            }
        }

    def merge_context_node(state: MainWorkflowState) -> Dict[str, Any]:
        merged_context: Dict[str, Any] = {"applied_steps": []}

        request_context = state.get("request_context")
        if isinstance(request_context, str) and request_context.strip():
            merged_context["request_context"] = request_context.strip()

        handoff = state.get("handoff")
        if isinstance(handoff, dict):
            merged_context["request_flags"] = {
                "ask_preprocess": bool(handoff.get("ask_preprocess", False)),
                "ask_visualization": bool(handoff.get("ask_visualization", False)),
                "ask_report": bool(handoff.get("ask_report", False)),
            }

        preprocess_result = state.get("preprocess_result")
        if isinstance(preprocess_result, dict):
            merged_context["preprocess_result"] = preprocess_result
            if preprocess_result.get("status") == "applied":
                merged_context["applied_steps"].append("preprocess")

        rag_result = state.get("rag_result")
        if isinstance(rag_result, dict):
            merged_context["rag_result"] = rag_result
            if int(rag_result.get("retrieved_count", 0) or 0) > 0:
                merged_context["applied_steps"].append("rag")

        insight = state.get("insight")
        if isinstance(insight, dict):
            merged_context["insight"] = insight
            summary = insight.get("summary")
            if isinstance(summary, str) and summary.strip():
                merged_context["applied_steps"].append("insight")

        visualization_result = state.get("visualization_result")
        if isinstance(visualization_result, dict):
            merged_context["visualization_result"] = visualization_result
            if visualization_result.get("status") == "generated":
                merged_context["applied_steps"].append("visualization")

        return {"merged_context": merged_context}

    def data_qa_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        merged_context = state.get("merged_context")
        answer = answer_data_question(
            user_input=str(state.get("user_input", "")),
            merged_context=merged_context if isinstance(merged_context, dict) else {},
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {
            "data_qa_result": {"content": answer},
            "output": {
                "type": "data_qa",
                "content": answer,
            },
        }

    graph = StateGraph(MainWorkflowState)
    graph.add_node("intake_flow", intake_graph)
    graph.add_node("general_question_terminal", general_question_terminal)
    graph.add_node("preprocess_flow", preprocess_graph)
    graph.add_node("rag_flow", rag_graph)
    graph.add_node("visualization_flow", visualization_graph)
    graph.add_node("merge_context", merge_context_node)
    graph.add_node("data_qa_terminal", data_qa_terminal)
    graph.add_node("report_flow", report_graph)

    graph.add_edge(START, "intake_flow")
    graph.add_conditional_edges(
        "intake_flow",
        route_after_intake,
        {
            "general_question": "general_question_terminal",
            "data_pipeline": "preprocess_flow",
        },
    )
    graph.add_conditional_edges(
        "preprocess_flow",
        route_after_preprocess,
        {
            "rag": "rag_flow",
            "cancelled": END,
        },
    )
    graph.add_conditional_edges(
        "rag_flow",
        route_after_rag,
        {
            "visualization": "visualization_flow",
            "merge_context": "merge_context",
        },
    )
    graph.add_conditional_edges(
        "visualization_flow",
        route_after_visualization,
        {
            "merge_context": "merge_context",
            "cancelled": END,
        },
    )
    graph.add_conditional_edges(
        "merge_context",
        route_after_merge_context,
        {
            "report": "report_flow",
            "data_qa": "data_qa_terminal",
        },
    )
    graph.add_edge("report_flow", END)
    graph.add_edge("data_qa_terminal", END)
    graph.add_edge("general_question_terminal", END)

    return graph.compile(checkpointer=checkpointer)
