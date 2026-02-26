from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

if __name__ == "__main__" and __package__ is None:
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[4]))

from backend.app.ai.agents.intake_router import build_intake_router_workflow
from backend.app.ai.agents.preprocess import build_preprocess_workflow
from backend.app.ai.agents.rag import build_rag_workflow
from backend.app.ai.agents.report import build_report_workflow
from backend.app.ai.agents.state import MainWorkflowState
from backend.app.ai.agents.visualization import build_visualization_workflow
from backend.app.core.db import SessionLocal

load_dotenv()


def build_main_workflow(
    *,
    db: Session,
    default_model: str = "gpt-5-nano",
):
    """최종 오케스트레이션 그래프를 조립한다."""
    intake_graph = build_intake_router_workflow(default_model=default_model)
    preprocess_graph = build_preprocess_workflow(
        db=db,
        default_model=default_model,
    )
    rag_graph = build_rag_workflow(
        db=db,
        default_model=default_model,
    )
    visualization_graph = build_visualization_workflow(
        db=db,
        default_model=default_model,
    )
    report_graph = build_report_workflow(
        db=db,
        default_model=default_model,
    )

    def route_after_intake(state: MainWorkflowState) -> str:
        """Intake handoff 기준으로 다음 경로를 분기한다."""
        branch = str((state.get("handoff") or {}).get("next_step", "general_question"))
        return branch

    def route_after_rag(state: MainWorkflowState) -> str:
        """RAG 이후 시각화 여부를 분기한다."""
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "merge_context"

    def route_after_merge_context(state: MainWorkflowState) -> str:
        """Merge Context 이후 리포트/데이터 QA를 분기한다."""
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_report", False)):
            return "report"
        return "data_qa"

    def general_question_terminal(state: MainWorkflowState) -> Dict[str, Any]:
        """데이터셋 미선택 일반 질문 경로를 종료한다."""
        model_name = state.get("model_id") or default_model
        llm = init_chat_model(model_name)
        result = llm.invoke(
            [
                SystemMessage(
                    content="사용자 질문에 간결하고 정확하게 답하라."
                ),
                HumanMessage(content=state.get("user_input", "")),
            ]
        )
        answer = result.content if isinstance(result.content, str) else str(result.content)

        return {
            "output": {
                "type": "general_question",
                "content": answer,
            }
        }

    def merge_context_node(state: MainWorkflowState) -> Dict[str, Any]:
        """누적 산출물을 단일 컨텍스트로 병합한다."""
        merged_context: Dict[str, Any] = {"applied_steps": []}

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
        """누적 컨텍스트 기반 데이터 QA 응답을 생성한다."""
        model_name = state.get("model_id") or default_model
        llm = init_chat_model(model_name)

        user_input = state.get("user_input", "")
        question = str(user_input).split("\n\ncontext:\n", 1)[0]
        merged_context = state.get("merged_context")
        context_json = (
            json.dumps(merged_context, ensure_ascii=False)
            if isinstance(merged_context, dict)
            else "{}"
        )

        result = llm.invoke(
            [
                SystemMessage(
                    content="주어진 merged_context를 근거로 사용자 데이터 질문에 간결하게 답하라."
                ),
                HumanMessage(
                    content=(
                        f"question:\n{question}\n\n"
                        f"merged_context:\n{context_json}"
                    )
                ),
            ]
        )
        answer = result.content if isinstance(result.content, str) else str(result.content)
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
    graph.add_edge("preprocess_flow", "rag_flow")
    graph.add_conditional_edges(
        "rag_flow",
        route_after_rag,
        {
            "visualization": "visualization_flow",
            "merge_context": "merge_context",
        },
    )
    graph.add_edge("visualization_flow", "merge_context")
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

    return graph.compile()


if __name__ == "__main__":
    def _save_main_workflow_png(
        *,
        output_path: str = "builder_workflow.png",
        model_name: str = "gpt-5-nano",
    ) -> Path:
        """최종 그래프를 PNG 이미지로 저장한다."""
        db = SessionLocal()
        try:
            main_workflow = build_main_workflow(
                db=db,
                default_model=model_name,
            )
            png_bytes = main_workflow.get_graph().draw_mermaid_png()
        finally:
            db.close()

        path = Path(output_path)
        path.write_bytes(png_bytes)
        return path.resolve()

    def _save_all_workflow_pngs(
        *,
        output_dir: str = "graph_outputs",
        model_name: str = "gpt-5-nano",
    ) -> Dict[str, Path]:
        """메인/서브 그래프 PNG를 한 번에 저장한다."""
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        intake_graph = build_intake_router_workflow(default_model=model_name)
        db = SessionLocal()
        try:
            visualization_graph = build_visualization_workflow(
                db=db,
                default_model=model_name,
            )
            report_graph = build_report_workflow(
                db=db,
                default_model=model_name,
            )
            preprocess_graph = build_preprocess_workflow(
                db=db,
                default_model=model_name,
            )
            rag_graph = build_rag_workflow(
                db=db,
                default_model=model_name,
            )
            main_graph = build_main_workflow(
                db=db,
                default_model=model_name,
            )
        finally:
            db.close()

        targets: Dict[str, tuple[Path, Any]] = {
            "main": (out_dir / "main_workflow.png", main_graph),
            "intake": (out_dir / "intake_workflow.png", intake_graph),
            "preprocess": (out_dir / "preprocess_workflow.png", preprocess_graph),
            "rag": (out_dir / "rag_workflow.png", rag_graph),
            "visualization": (out_dir / "visualization_workflow.png", visualization_graph),
            "report": (out_dir / "report_workflow.png", report_graph),
        }

        saved_paths: Dict[str, Path] = {}
        for key, (path, graph_obj) in targets.items():
            png_bytes = graph_obj.get_graph().draw_mermaid_png()
            path.write_bytes(png_bytes)
            saved_paths[key] = path.resolve()

        return saved_paths

    saved = _save_all_workflow_pngs()
    for name, path in saved.items():
        print(f"{name}: {path}")
