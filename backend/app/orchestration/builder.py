from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from .ai import answer_data_question, answer_general_question
from .intake_router import build_intake_router_workflow
from ..modules.planner.service import build_handoff_from_planning_result
from .state import MainWorkflowState
from .state_view import build_merged_context
from .workflows.analysis import build_analysis_workflow
from .workflows.guideline import build_guideline_workflow
from .workflows.preprocess import build_preprocess_workflow
from .workflows.rag import build_rag_workflow
from .workflows.report import build_report_workflow
from .workflows.visualization import build_visualization_workflow


def build_main_workflow(
    *,
    planner_service,
    analysis_service,
    preprocess_service,
    eda_service,
    rag_service,
    guideline_service,
    guideline_rag_service,
    visualization_service,
    report_service,
    default_model: str = "gpt-5-nano",
    checkpointer: Any | None = None,
):
    intake_graph = build_intake_router_workflow(
        planner_service=planner_service,
    )
    preprocess_graph = build_preprocess_workflow(
        preprocess_service=preprocess_service,
        eda_service=eda_service,
        default_model=default_model,
    )
    analysis_graph = build_analysis_workflow(
        analysis_service=analysis_service,
        default_model=default_model,
    )
    rag_graph = build_rag_workflow(
        rag_service=rag_service,
        default_model=default_model,
    )
    guideline_graph = build_guideline_workflow(
        guideline_service=guideline_service,
        guideline_rag_service=guideline_rag_service,
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

    def route_after_planner(state: MainWorkflowState) -> str:
        if state.get("final_status") == "fail":
            return "fail"

        planning_result = state.get("planning_result") or {}
        if bool(planning_result.get("needs_clarification", False)):
            return "clarification"

        route = str(planning_result.get("route", "fallback_rag"))
        if route == "general_question":
            return "general_question"
        if route == "fallback_rag":
            return "rag"
        if bool(planning_result.get("preprocess_required", False)):
            return "preprocess"
        return "analysis"

    def route_after_rag(state: MainWorkflowState) -> str:
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "merge_context"

    def route_after_preprocess(state: MainWorkflowState) -> str:
        preprocess_result = state.get("preprocess_result") or {}
        output = state.get("output") or {}
        if (
            preprocess_result.get("status") == "cancelled"
            or output.get("type") == "cancelled"
        ):
            return "cancelled"
        if (
            preprocess_result.get("status") == "failed"
            or output.get("type") == "preprocess_failed"
        ):
            return "failed"
        return "analysis"

    def route_after_analysis(state: MainWorkflowState) -> str:
        final_status = state.get("final_status")
        if final_status == "needs_clarification":
            return "clarification"
        if final_status == "fail":
            return "fail"

        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "merge_context"

    def route_after_merge_context(state: MainWorkflowState) -> str:
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_report", False)):
            return "report"
        return "data_qa"

    def route_after_visualization(state: MainWorkflowState) -> str:
        visualization_result = state.get("visualization_result") or {}
        output = state.get("output") or {}
        if (
            visualization_result.get("status") == "cancelled"
            or output.get("type") == "cancelled"
        ):
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

    def clarification_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        clarification_question = str(state.get("clarification_question", "")).strip()
        return {
            "output": {
                "type": "clarification",
                "content": clarification_question,
            }
        }

    def merge_context_node(state: MainWorkflowState) -> Dict[str, Any]:
        return {"merged_context": build_merged_context(state)}

    def dataset_context_node(state: MainWorkflowState) -> Dict[str, Any]:
        source_id = str(state.get("source_id") or "").strip()
        dataset_context = planner_service.dataset_context_service.build_context(source_id)
        return {"dataset_context": dataset_context.model_dump()}

    def planner_node(state: MainWorkflowState) -> Dict[str, Any]:
        try:
            planning_result = planner_service.plan(
                user_input=str(state.get("user_input", "")),
                request_context=str(state.get("request_context", "")),
                source_id=str(state.get("source_id", "")),
                dataset_context=state.get("dataset_context"),
                guideline_context=state.get("guideline_context"),
                model_id=state.get("model_id"),
            )
        except Exception as exc:
            return {
                "final_status": "fail",
                "output": {
                    "type": "planning_failed",
                    "content": str(exc),
                },
            }

        return {
            "planning_result": planning_result.model_dump(),
            "handoff": build_handoff_from_planning_result(planning_result),
            "clarification_question": planning_result.clarification_question,
        }

    def data_qa_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        merged_context = state.get("merged_context")
        answer = answer_data_question(
            user_input=str(state.get("user_input", "")),
            merged_context=merged_context if isinstance(merged_context, dict) else {},
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        answer_text = str(answer or "").strip()
        return {
            "data_qa_result": {"content": answer_text},
            "output": {
                "type": "data_qa",
                "content": answer_text,
            },
        }

    graph = StateGraph(MainWorkflowState)
    graph.add_node("intake_flow", intake_graph)
    graph.add_node("general_question_terminal", general_question_terminal)
    graph.add_node("clarification_terminal", clarification_terminal)
    graph.add_node("dataset_context", dataset_context_node)
    graph.add_node("planner", planner_node)
    graph.add_node("preprocess_flow", preprocess_graph)
    graph.add_node("analysis_flow", analysis_graph)
    graph.add_node("rag_flow", rag_graph)
    graph.add_node("guideline_flow", guideline_graph)
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
            "dataset_selected": "dataset_context",
        },
    )
    graph.add_edge("dataset_context", "guideline_flow")
    graph.add_edge("guideline_flow", "planner")
    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "general_question": "general_question_terminal",
            "preprocess": "preprocess_flow",
            "analysis": "analysis_flow",
            "rag": "rag_flow",
            "clarification": "clarification_terminal",
            "fail": END,
        },
    )
    graph.add_conditional_edges(
        "preprocess_flow",
        route_after_preprocess,
        {
            "analysis": "analysis_flow",
            "cancelled": END,
            "failed": END,
        },
    )
    graph.add_conditional_edges(
        "analysis_flow",
        route_after_analysis,
        {
            "visualization": "visualization_flow",
            "merge_context": "merge_context",
            "clarification": "clarification_terminal",
            "fail": END,
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
    graph.add_edge("clarification_terminal", END)

    return graph.compile(checkpointer=checkpointer)
