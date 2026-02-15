from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_config
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
from backend.app.ai.tools.general import TOOLS
from backend.app.core.db import SessionLocal

load_dotenv()


@lru_cache(maxsize=8)
def _cached_model(model_name: str):
    return init_chat_model(model_name)


class AgentBuilder:
    """LangChain create_agent 빌더."""

    def __init__(self, model_name: str = "gpt-5-nano"):
        self.model = model_name
        self.tools = TOOLS
        self.checkpointer = InMemorySaver()

    def build(self):
        """기본 에이전트를 생성한다."""
        return create_agent(
            model=self.model,
            tools=self.tools,
            middleware=[self.dynamic_model_selector],
            checkpointer=self.checkpointer,
        )

    @staticmethod
    @wrap_model_call
    def dynamic_model_selector(request, handler):
        """configurable.model_id가 있으면 요청 모델을 동적으로 교체한다."""
        config = get_config() or {}
        model_id = config.get("configurable", {}).get("model_id")
        if model_id and model_id != request.model:
            return handler(request.override(model=_cached_model(model_id)))
        return handler(request)


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
    rag_graph = build_rag_workflow(default_model=default_model)
    visualization_graph = build_visualization_workflow(default_model=default_model)
    report_graph = build_report_workflow(default_model=default_model)

    def route_after_intake(state: MainWorkflowState) -> str:
        """Intake handoff 기준으로 다음 경로를 분기한다."""
        branch = str((state.get("handoff") or {}).get("next_step", "general_question"))
        return branch

    def route_after_preprocess(state: MainWorkflowState) -> str:
        """전처리 이후 요청 플래그 기준으로 RAG/시각화/리포트 분기를 결정한다."""
        handoff = state.get("handoff") or {}
        if bool(handoff.get("ask_report", False)):
            return "report"
        if bool(handoff.get("ask_visualization", False)):
            return "visualization"
        return "rag"

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

    graph = StateGraph(MainWorkflowState)
    graph.add_node("intake_flow", intake_graph)
    graph.add_node("general_question_terminal", general_question_terminal)
    graph.add_node("preprocess_flow", preprocess_graph)
    graph.add_node("rag_flow", rag_graph)
    graph.add_node("visualization_flow", visualization_graph)
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
            "visualization": "visualization_flow",
            "report": "report_flow",
        },
    )
    graph.add_edge("rag_flow", END)
    graph.add_edge("visualization_flow", END)
    graph.add_edge("report_flow", END)
    graph.add_edge("general_question_terminal", END)

    return graph.compile()


class WorkflowBuilder:
    """최종 오케스트레이션 그래프 생성기."""

    def __init__(self, *, db: Session, model_name: str = "gpt-5-nano"):
        self.db = db
        self.model_name = model_name

    def build(self):
        """최종 그래프를 생성한다."""
        return build_main_workflow(
            db=self.db,
            default_model=self.model_name,
        )


def save_main_workflow_png(
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


def save_all_workflow_pngs(
    *,
    output_dir: str = "graph_outputs",
    model_name: str = "gpt-5-nano",
) -> Dict[str, Path]:
    """메인/서브 그래프 PNG를 한 번에 저장한다."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    intake_graph = build_intake_router_workflow(default_model=model_name)
    rag_graph = build_rag_workflow(default_model=model_name)
    visualization_graph = build_visualization_workflow(default_model=model_name)
    report_graph = build_report_workflow(default_model=model_name)

    db = SessionLocal()
    try:
        preprocess_graph = build_preprocess_workflow(
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


if __name__ == "__main__":
    saved = save_all_workflow_pngs()
    for name, path in saved.items():
        print(f"{name}: {path}")
