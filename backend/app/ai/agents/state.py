"""
에이전트 그래프 전반에서 공유하는 공통 상태 정의.
"""

from __future__ import annotations

from typing import Any, Dict, TypedDict


class AgentState(TypedDict, total=False):
    """
    여러 그래프 노드가 공통으로 참조할 입력/컨텍스트 상태.
    """

    user_input: str
    user_context: Dict[str, Any]
    session_id: str
    model_id: str
    dataset_id: int
    source_id: str
    dataset_profile: Dict[str, Any]


class IntakeRouterState(AgentState, total=False):
    """Intake Router 전용 상태."""

    intent: Dict[str, Any]
    handoff: Dict[str, Any]


class PreprocessGraphState(AgentState, total=False):
    """Preprocess 서브그래프 전용 상태."""

    preprocess_decision: Dict[str, Any]
    preprocess_plan: Dict[str, Any]
    preprocess_result: Dict[str, Any]


class RagGraphState(AgentState, total=False):
    """RAG 서브그래프 전용 상태."""

    preprocess_result: Dict[str, Any]
    rag_data_exists: bool
    rag_result: Dict[str, Any]
    insight: Dict[str, Any]


class VisualizationGraphState(AgentState, total=False):
    """시각화 서브그래프 전용 상태."""

    handoff: Dict[str, Any]
    insight: Dict[str, Any]
    visualization_plan: Dict[str, Any]
    visualization_result: Dict[str, Any]


class ReportGraphState(AgentState, total=False):
    """리포트 서브그래프 전용 상태."""

    handoff: Dict[str, Any]
    insight: Dict[str, Any]
    visualization_result: Dict[str, Any]
    report_result: Dict[str, Any]
    output: Dict[str, Any]


class MainWorkflowState(AgentState, total=False):
    """최종 워크플로우 그래프 전용 상태."""

    intent: Dict[str, Any]
    handoff: Dict[str, Any]
    preprocess_decision: Dict[str, Any]
    preprocess_plan: Dict[str, Any]
    preprocess_result: Dict[str, Any]
    rag_data_exists: bool
    rag_result: Dict[str, Any]
    insight: Dict[str, Any]
    visualization_plan: Dict[str, Any]
    visualization_result: Dict[str, Any]
    report_result: Dict[str, Any]
    output: Dict[str, Any]


CommonAgentState = AgentState
