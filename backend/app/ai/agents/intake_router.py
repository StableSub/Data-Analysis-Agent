"""
V1 Intake Router (Intent only).

역할:
- 데이터셋 선택 여부 + 사용자 의도만 분기한다.
- 실제 데이터 파이프라인 실행은 builder.py의 최종 그래프가 담당한다.
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from backend.app.ai.agents.state import IntakeRouterState
from backend.app.ai.agents.utils import call_structured_llm


class IntentDecision(BaseModel):
    step: Literal["general_question", "data_pipeline"] = Field(...)
    ask_preprocess: bool = Field(False)
    ask_visualization: bool = Field(False)
    ask_report: bool = Field(False)


def build_intake_router_workflow(default_model: str = "gpt-5-nano"):
    """
    역할: 데이터셋 선택 여부와 사용자 의도를 분석해 handoff만 결정하는 intake 라우터 그래프를 만든다.
    입력: 기본 모델명(`default_model`)을 받아 의도 분석 LLM 호출의 기본값으로 사용한다.
    출력: `general_question` 또는 `data_pipeline` handoff를 반환하는 컴파일된 그래프를 반환한다.
    데코레이터: 없음.
    호출 맥락: 메인 워크플로우의 첫 단계(`intake_flow`)로 연결되어 전체 분기 방향을 정한다.
    """

    def route_dataset_selected(state: IntakeRouterState) -> str:
        """
        역할: 입력 상태에 데이터셋 source가 있는지 확인해 첫 분기 키를 산출한다.
        입력: `state.source_id`가 포함된 intake 상태를 받는다.
        출력: source 존재 시 `data_selected`, 없으면 `no_dataset` 문자열을 반환한다.
        데코레이터: 없음.
        호출 맥락: intake 그래프 START 이후 conditional edge 라우터로 즉시 실행된다.
        """
        source_id = state.get("source_id")
        return "data_selected" if source_id else "no_dataset"

    def general_question_node(_: IntakeRouterState) -> Dict[str, Any]:
        """
        역할: 데이터셋 미선택 요청을 일반 질의 경로로 넘기기 위한 handoff를 생성한다.
        입력: intake 상태를 받지만 실제 값은 사용하지 않는다.
        출력: `handoff.next_step=general_question`를 담은 상태 업데이트 딕셔너리를 반환한다.
        데코레이터: 없음.
        호출 맥락: `route_dataset_selected` 결과가 `no_dataset`일 때 실행되는 경량 노드다.
        """
        return {"handoff": {"next_step": "general_question"}}

    def analyze_intent_node(state: IntakeRouterState) -> Dict[str, Any]:
        """
        역할: 데이터셋이 이미 선택된 요청에서 전처리/시각화/리포트 의도를 구조화 출력으로 분류한다.
        입력: `state.user_input`, `state.model_id`를 포함한 intake 상태를 받는다.
        출력: `IntentDecision` 결과를 `intent` 키로 담은 상태 업데이트를 반환한다.
        데코레이터: 없음.
        호출 맥락: `data_selected` 분기에서 호출되며 이후 데이터 파이프라인 handoff 생성을 위한 전 단계다.
        """
        decision = call_structured_llm(
            schema=IntentDecision,
            system_prompt=(
                "데이터셋이 이미 선택된 상황이다. "
                "step은 data_pipeline으로 반환하라. "
                "질문을 보고 ask_preprocess, ask_visualization, ask_report를 true/false로 판단하라."
            ),
            human_prompt=state.get("user_input", ""),
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        return {"intent": decision.model_dump()}

    def data_pipeline_node(state: IntakeRouterState) -> Dict[str, Any]:
        """
        역할: intent 결과를 메인 그래프가 이해하는 `handoff` 플래그 묶음으로 변환한다.
        입력: `state.intent` 내 ask_preprocess/ask_visualization/ask_report 값을 읽는다.
        출력: `handoff.next_step=data_pipeline`과 세부 요청 플래그를 담은 딕셔너리를 반환한다.
        데코레이터: 없음.
        호출 맥락: intake 그래프의 마지막 노드로 메인 워크플로우의 데이터 경로 진입 신호를 만든다.
        """
        intent = state.get("intent") or {}
        return {
            "handoff": {
                "next_step": "data_pipeline",
                "ask_preprocess": bool(intent.get("ask_preprocess", False)),
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
    graph.add_edge("analyze_intent", "data_pipeline_handoff")
    graph.add_edge("general_question_handoff", END)
    graph.add_edge("data_pipeline_handoff", END)

    return graph.compile()


# Backward-compatible alias
build_preprocess_intake_workflow = build_intake_router_workflow
