from __future__ import annotations

from typing import Any, Dict, Literal, TypedDict

from ..modules.analysis.schemas import FinalStatus, VisualizationOutput


class HandoffPayload(TypedDict, total=False):
    next_step: str
    ask_analysis: bool
    ask_preprocess: bool
    ask_visualization: bool
    ask_report: bool
    ask_guideline: bool


class PreprocessResultPayload(TypedDict, total=False):
    status: str
    summary: str
    applied_ops_count: int
    input_source_id: str
    output_source_id: str
    output_filename: str
    error: str


class RagResultPayload(TypedDict, total=False):
    status: str
    has_evidence: bool
    query: str
    source_id: str
    retrieved_chunks: list
    context: str
    retrieved_count: int
    evidence_summary: str


class GuidelineResultPayload(TypedDict, total=False):
    has_evidence: bool
    query: str
    source_id: str
    guideline_id: str
    filename: str
    retrieved_chunks: list
    context: str
    retrieved_count: int
    evidence_summary: str
    status: str


class VisualizationResultPayload(TypedDict, total=False):
    status: str
    source_id: str
    summary: str
    chart: Dict[str, Any]
    artifact: Dict[str, Any]


class ReportResultPayload(TypedDict, total=False):
    status: str
    summary: str
    error: str
    report_id: str
    metrics: Dict[str, Any]
    visualizations: list[Dict[str, Any]]
    revision_count: int


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
    source_id: str
    active_guideline_source_id: str
    analysis_run_id: str
    clarification_question: str
    clarification_answer: str
    dataset_profile: Dict[str, Any]
    pending_approval: PendingApprovalPayload
    revision_request: RevisionRequestPayload
    approved_plan: Dict[str, Any]
    dataset_meta: Dict[str, Any]
    question_understanding: Dict[str, Any]
    column_grounding: Dict[str, Any]
    analysis_plan_draft: Dict[str, Any]
    analysis_plan: Dict[str, Any]
    sandbox_result: Dict[str, Any]
    analysis_result: Dict[str, Any]
    analysis_error: Dict[str, Any]


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


class GuidelineGraphState(AgentState, total=False):
    """Guideline 서브그래프 전용 상태."""

    handoff: HandoffPayload
    guideline_index_status: Dict[str, Any]
    guideline_data_exists: bool
    guideline_result: GuidelineResultPayload


class AnalysisGraphState(AgentState, total=False):
    """Analysis 서브그래프 전용 상태."""

    handoff: HandoffPayload
    generated_code: str
    validated_code: str
    retry_count: int
    final_status: FinalStatus


class VisualizationGraphState(AgentState, total=False):
    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_result: RagResultPayload
    guideline_result: GuidelineResultPayload
    insight: Dict[str, Any]
    visualization_plan: Dict[str, Any]
    visualization_result: VisualizationResultPayload
    output: OutputPayload


class ReportGraphState(AgentState, total=False):
    handoff: HandoffPayload
    preprocess_result: PreprocessResultPayload
    rag_result: RagResultPayload
    guideline_result: GuidelineResultPayload
    insight: Dict[str, Any]
    visualization_result: VisualizationResultPayload
    merged_context: Dict[str, Any]
    report_draft: Dict[str, Any]
    report_result: ReportResultPayload
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
    guideline_index_status: Dict[str, Any]
    guideline_data_exists: bool
    guideline_result: GuidelineResultPayload
    insight: Dict[str, Any]

    final_status: FinalStatus

    visualization_plan: Dict[str, Any]
    visualization_result: VisualizationResultPayload
    visualization_output: VisualizationOutput
    merged_context: Dict[str, Any]
    report_draft: Dict[str, Any]
    report_result: ReportResultPayload
    data_qa_result: Dict[str, Any]

    output: OutputPayload
