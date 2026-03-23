from __future__ import annotations

from typing import Any, Dict, Literal, TypedDict


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


class PendingApprovalPayload(TypedDict, total=False):
    stage: Literal["preprocess", "visualization", "report"]
    kind: Literal["plan_review", "draft_review"]
    title: str
    summary: str
    source_id: str
    plan: Dict[str, Any]
    draft: str
    review: Dict[str, Any]


class RevisionRequestPayload(TypedDict, total=False):
    stage: Literal["preprocess", "visualization", "report"]
    instruction: str


class AgentState(TypedDict, total=False):
    user_input: str
    request_context: str
    session_id: str
    model_id: str
    run_id: str
    dataset_id: int
    source_id: str
    dataset_profile: Dict[str, Any]
    pending_approval: PendingApprovalPayload
    revision_request: RevisionRequestPayload
    approved_plan: Dict[str, Any]


class IntakeRouterState(AgentState, total=False):
    intent: Dict[str, Any]
    handoff: HandoffPayload


class PreprocessGraphState(AgentState, total=False):
    handoff: HandoffPayload
    preprocess_decision: Dict[str, Any]
    preprocess_plan: Dict[str, Any]
    preprocess_result: PreprocessResultPayload
    output: OutputPayload


class RagGraphState(AgentState, total=False):
    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_index_status: Dict[str, Any]
    rag_data_exists: bool
    rag_result: RagResultPayload
    insight: Dict[str, Any]


class VisualizationGraphState(AgentState, total=False):
    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_result: RagResultPayload
    insight: Dict[str, Any]
    visualization_plan: Dict[str, Any]
    visualization_result: VisualizationResultPayload
    output: OutputPayload


class ReportGraphState(AgentState, total=False):
    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_result: RagResultPayload
    insight: Dict[str, Any]
    visualization_result: VisualizationResultPayload
    merged_context: Dict[str, Any]
    report_draft: Dict[str, Any]
    report_result: Dict[str, Any]
    output: OutputPayload


class MainWorkflowState(AgentState, total=False):
    intent: Dict[str, Any]
    handoff: HandoffPayload

    preprocess_decision: Dict[str, Any]
    preprocess_plan: Dict[str, Any]
    preprocess_result: PreprocessResultPayload

    rag_index_status: Dict[str, Any]
    rag_data_exists: bool
    rag_result: RagResultPayload
    insight: Dict[str, Any]

    visualization_plan: Dict[str, Any]
    visualization_result: VisualizationResultPayload
    merged_context: Dict[str, Any]
    report_draft: Dict[str, Any]
    report_result: Dict[str, Any]
    data_qa_result: Dict[str, Any]

    output: OutputPayload


CommonAgentState = AgentState
