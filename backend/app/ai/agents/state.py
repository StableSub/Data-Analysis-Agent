"""
에이전트 그래프 전반에서 공유하는 공통 상태 정의.
"""

from __future__ import annotations

from typing import Any, Dict, TypedDict


class HandoffPayload(TypedDict, total=False):
    next_step: str
    ask_preprocess: bool
    ask_visualization: bool
    ask_report: bool


class PreprocessResultPayload(TypedDict, total=False):
    status: str
    applied_ops_count: int
    input_source_id: str
    output_source_id: str
    output_filename: str
    error: str


class RagResultPayload(TypedDict, total=False):
    query: str
    source_id: str
    retrieved_chunks: list
    context: str
    retrieved_count: int
    evidence_summary: str


class VisualizationResultPayload(TypedDict, total=False):
    status: str
    source_id: str
    summary: str
    chart: Dict[str, Any]
    artifact: Dict[str, Any]


class OutputPayload(TypedDict, total=False):
    type: str
    content: str


class AgentState(TypedDict, total=False):
    """
    여러 그래프 노드가 공통으로 참조할 입력/컨텍스트 상태.
    """

    user_input: str
    session_id: str
    model_id: str
    dataset_id: int
    source_id: str
    dataset_profile: Dict[str, Any]


class IntakeRouterState(AgentState, total=False):
    """Intake Router 전용 상태."""

    intent: Dict[str, Any]
    handoff: HandoffPayload


class PreprocessGraphState(AgentState, total=False):
    """Preprocess 서브그래프 전용 상태."""

    handoff: HandoffPayload
    preprocess_decision: Dict[str, Any]
    preprocess_plan: Dict[str, Any]
    preprocess_result: PreprocessResultPayload


class RagGraphState(AgentState, total=False):
    """RAG 서브그래프 전용 상태."""

    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_index_status: Dict[str, Any]
    rag_data_exists: bool
    rag_result: RagResultPayload
    insight: Dict[str, Any]


class VisualizationGraphState(AgentState, total=False):
    """시각화 서브그래프 전용 상태."""

    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_result: RagResultPayload
    insight: Dict[str, Any]
    # visualization_plan: {"status","source_id","mode","chart_type","x_key","y_key","reason","python_code","output_filename"}
    visualization_plan: Dict[str, Any]
    # visualization_result: {"status","source_id","summary","chart?":{"chart_type","x_key","y_key"},"artifact?":{"mime_type","image_base64","code"}}
    visualization_result: VisualizationResultPayload


class ReportGraphState(AgentState, total=False):
    """리포트 서브그래프 전용 상태."""

    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_result: RagResultPayload
    insight: Dict[str, Any]
    # visualization_result.chart/artifact를 리포트 본문/메타에 반영
    visualization_result: VisualizationResultPayload
    merged_context: Dict[str, Any]
    # report_result: {"summary","metrics","visualizations":[{"chart","artifact?"}]}
    report_result: Dict[str, Any]
    output: OutputPayload


class MainWorkflowState(AgentState, total=False):
    """최종 워크플로우 그래프 전용 상태."""

    # intake/handoff
    intent: Dict[str, Any]
    handoff: HandoffPayload

    # preprocess
    preprocess_decision: Dict[str, Any]
    preprocess_plan: Dict[str, Any]
    preprocess_result: PreprocessResultPayload

    # rag/insight (내부 처리용 상태, SSE done에서는 직접 노출하지 않음)
    rag_index_status: Dict[str, Any]
    rag_data_exists: bool
    rag_result: RagResultPayload
    insight: Dict[str, Any]

    # visualization/report/data qa (내부 처리용 상태, SSE done에서는 직접 노출하지 않음)
    visualization_plan: Dict[str, Any]
    # chart+artifact payload 포함 가능: {"status","summary","chart","artifact"}
    visualization_result: VisualizationResultPayload
    merged_context: Dict[str, Any]
    # report_result: {"summary","metrics","visualizations":[{"chart","artifact?"}]}
    report_result: Dict[str, Any]
    data_qa_result: Dict[str, Any]

    # 최종 사용자 응답
    output: OutputPayload


CommonAgentState = AgentState
