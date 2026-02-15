"""
V1 Intake Router (Intent only).

역할:
- 데이터셋 선택 여부 + 사용자 의도만 분기한다.
- 실제 데이터 파이프라인 실행은 builder.py의 최종 그래프가 담당한다.
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from backend.app.ai.agents.state import IntakeRouterState


class IntentDecision(BaseModel):
    step: Literal["general_question", "data_pipeline"] = Field(...)
    ask_visualization: bool = Field(False)
    ask_report: bool = Field(False)


def build_intake_router_workflow(default_model: str = "gpt-5-nano"):
    """의도 분기 전용 라우터 그래프를 생성한다."""

    def log_branch(point: str, branch: str, detail: str = "") -> None:
        """분기 지점과 선택 결과를 콘솔에 출력한다."""
        suffix = f" | {detail}" if detail else ""
        print(f"[branch:intake] {point} -> {branch}{suffix}")

    def call_structured(
        schema: type[BaseModel],
        system_prompt: str,
        human_prompt: str,
        model_id: str | None,
    ):
        """구조화 출력이 필요한 LLM 호출을 수행한다."""
        model_name = model_id or default_model
        llm = init_chat_model(model_name).with_structured_output(schema)
        return llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]
        )

    def route_dataset_selected(state: IntakeRouterState) -> str:
        """dataset_id 존재 여부로 첫 분기를 수행한다."""
        branch = "data_selected" if state.get("dataset_id") else "no_dataset"
        log_branch("dataset_selected", branch, f"dataset_id={state.get('dataset_id')}")
        return branch

    def general_question_node(_: IntakeRouterState) -> Dict[str, Any]:
        """데이터셋이 없으면 일반 질문 경로로 handoff를 생성한다."""
        log_branch("handoff", "general_question")
        return {"handoff": {"next_step": "general_question"}}

    def analyze_intent_node(state: IntakeRouterState) -> Dict[str, Any]:
        """데이터셋 선택 상태에서 사용자 의도를 분석한다."""
        decision = call_structured(
            IntentDecision,
            (
                "사용자 의도를 분류하라. "
                "데이터셋 기반 처리가 필요하면 data_pipeline, "
                "아니면 general_question을 반환하라."
            ),
            state.get("user_input", ""),
            state.get("model_id"),
        )
        log_branch(
            "intent_analysis",
            decision.step,
            f"ask_visualization={decision.ask_visualization}, ask_report={decision.ask_report}",
        )
        return {"intent": decision.model_dump()}

    def route_after_intent(state: IntakeRouterState) -> str:
        """의도 분석 결과에 따라 일반 질문/데이터 파이프라인 경로를 결정한다."""
        branch = str((state.get("intent") or {}).get("step", "general_question"))
        log_branch("after_intent", branch)
        return branch

    def data_pipeline_node(state: IntakeRouterState) -> Dict[str, Any]:
        """최종 빌더 그래프의 데이터 파이프라인 시작 신호를 전달한다."""
        intent = state.get("intent") or {}
        log_branch(
            "handoff",
            "data_pipeline",
            (
                f"ask_visualization={bool(intent.get('ask_visualization', False))}, "
                f"ask_report={bool(intent.get('ask_report', False))}"
            ),
        )
        return {
            "handoff": {
                "next_step": "data_pipeline",
                "ask_visualization": bool(intent.get("ask_visualization", False)),
                "ask_report": bool(intent.get("ask_report", False)),
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
    graph.add_conditional_edges(
        "analyze_intent",
        route_after_intent,
        {
            "general_question": "general_question_handoff",
            "data_pipeline": "data_pipeline_handoff",
        },
    )
    graph.add_edge("general_question_handoff", END)
    graph.add_edge("data_pipeline_handoff", END)

    return graph.compile()


# Backward-compatible alias
build_preprocess_intake_workflow = build_intake_router_workflow
