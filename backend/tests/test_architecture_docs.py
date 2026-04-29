from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
ARCHITECTURE_DIR = REPO_ROOT / "docs" / "architecture"
BACKEND_WORKFLOW_DOC = ARCHITECTURE_DIR / "backend-workflow.md"
ORCHESTRATION_DOC = ARCHITECTURE_DIR / "orchestration" / "README.md"
WORKFLOW_WRAPPERS_DOC = ARCHITECTURE_DIR / "orchestration" / "workflows.md"
ORCHESTRATION_DIR = REPO_ROOT / "backend" / "app" / "orchestration"
FRONTEND_STRUCTURE = DOCS_DIR / "system" / "frontend-structure.md"
WORKFLOWS_DIR = ORCHESTRATION_DIR / "workflows"

COMPONENT_IMPLEMENTATION_FILES = {
    "main-workflow.md": ORCHESTRATION_DIR / "builder.py",
    "guideline.md": WORKFLOWS_DIR / "guideline.py",
    "preprocess.md": WORKFLOWS_DIR / "preprocess.py",
    "analysis.md": WORKFLOWS_DIR / "analysis.py",
    "rag.md": WORKFLOWS_DIR / "rag.py",
    "visualization.md": WORKFLOWS_DIR / "visualization.py",
    "report.md": WORKFLOWS_DIR / "report.py",
}

COMPONENT_STATUS_TERMS = {
    "main-workflow.md": (
        "general_question",
        "data_pipeline",
        "analysis",
        "rag",
        "guideline",
        "visualization",
        "merge_context",
        "clarification",
        "fail",
        "cancelled",
        "report",
        "data_qa",
        "report_answer",
        "applied",
        "generated",
    ),
    "guideline.md": (
        "no_active_guideline",
        "existing",
        "created",
        "missing",
        "retrieved",
        "no_evidence",
    ),
    "preprocess.md": (
        "run_preprocess",
        "skip_preprocess",
        "approve",
        "revise",
        "cancel",
        "skipped",
        "applied",
        "failed",
        "cancelled",
    ),
    "analysis.md": (
        "planning",
        "needs_clarification",
        "executing",
        "success",
        "fail",
        "analysis_failed",
    ),
    "rag.md": (
        "existing",
        "created",
        "dataset_missing",
        "unsupported_format",
    ),
    "visualization.md": (
        "analysis_generated",
        "planned",
        "approve",
        "revise",
        "cancel",
        "generated",
        "cancelled",
    ),
    "report.md": (
        "approve",
        "revise",
        "cancel",
        "report_answer",
        "cancelled",
    ),
}

COMPONENT_PAYLOAD_TERMS = {
    "main-workflow.md": (
        "user_input",
        "request_context",
        "handoff",
        "preprocess_result",
        "rag_result",
        "guideline_index_status",
        "guideline_result",
        "insight",
        "analysis_plan",
        "analysis_result",
        "visualization_result",
        "clarification_question",
        "model_id",
        "output",
        "merged_context",
    ),
    "guideline.md": (
        "user_input",
        "model_id",
        "active_guideline_source_id",
        "guideline_index_status",
        "guideline_result",
        "guideline_data_exists",
        "retrieved_chunks",
        "retrieved_count",
        "evidence_summary",
        "status",
    ),
    "preprocess.md": (
        "source_id",
        "dataset_profile",
        "handoff",
        "revision_request",
        "user_input",
        "model_id",
        "preprocess_decision",
        "preprocess_plan",
        "approved_plan",
        "pending_approval",
        "preprocess_result",
        "output",
        "output_source_id",
    ),
    "analysis.md": (
        "user_input",
        "source_id",
        "model_id",
        "analysis_plan",
        "session_id",
        "dataset_meta",
        "question_understanding",
        "column_grounding",
        "analysis_plan_draft",
        "generated_code",
        "validated_code",
        "sandbox_result",
        "analysis_result",
        "analysis_error",
        "retry_count",
        "final_status",
        "clarification_question",
        "analysis_result_id",
        "output",
    ),
    "rag.md": (
        "user_input",
        "source_id",
        "model_id",
        "rag_index_status",
        "rag_result",
        "rag_data_exists",
        "insight",
        "retrieved_chunks",
        "retrieved_count",
        "evidence_summary",
    ),
    "visualization.md": (
        "analysis_result",
        "analysis_plan",
        "source_id",
        "dataset_profile",
        "revision_request",
        "model_id",
        "user_input",
        "visualization_plan",
        "visualization_result",
        "approved_plan",
        "pending_approval",
        "output",
        "renderer",
        "vega_lite_spec",
    ),
    "report.md": (
        "user_input",
        "source_id",
        "analysis_result",
        "visualization_result",
        "guideline_result",
        "insight",
        "merged_context",
        "revision_request",
        "report_draft",
        "model_id",
        "report_result",
        "pending_approval",
        "output",
    ),
}

APPROVAL_COMPONENT_CONTRACTS = {
    "preprocess.md": ("pending_approval.stage=\"preprocess\"", "pending_approval.kind=\"plan_review\"", "revision_request.stage=\"preprocess\""),
    "visualization.md": ("pending_approval.stage=\"visualization\"", "pending_approval.kind=\"plan_review\"", "revision_request.stage=\"visualization\""),
    "report.md": ("pending_approval.stage=\"report\"", "pending_approval.kind=\"draft_review\"", "revision_request.stage=\"report\""),
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _workflow_contract_content() -> str:
    return "\n".join(
        _read_text(path)
        for path in (
            BACKEND_WORKFLOW_DOC,
            ORCHESTRATION_DOC,
            WORKFLOW_WRAPPERS_DOC,
            ARCHITECTURE_DIR / "shared-state.md",
        )
    )


def test_architecture_docs_exist() -> None:
    assert (ARCHITECTURE_DIR / "README.md").exists()
    assert BACKEND_WORKFLOW_DOC.exists()
    assert (ARCHITECTURE_DIR / "request-lifecycle.md").exists()
    assert (ARCHITECTURE_DIR / "shared-state.md").exists()
    assert (ARCHITECTURE_DIR / "core" / "README.md").exists()
    assert (ARCHITECTURE_DIR / "modules" / "README.md").exists()
    assert ORCHESTRATION_DOC.exists()
    assert WORKFLOW_WRAPPERS_DOC.exists()
    assert (DOCS_DIR / "system" / "api-spec.md").exists()
    assert (DOCS_DIR / "system" / "backend-structure.md").exists()
    assert FRONTEND_STRUCTURE.exists()
    assert (DOCS_DIR / "ai-agent" / "trace-and-logging.md").exists()


def test_readme_links_top_level_and_component_docs() -> None:
    content = _read_text(ARCHITECTURE_DIR / "README.md")

    assert "./request-lifecycle.md" in content
    assert "./shared-state.md" in content
    assert "./backend-workflow.md" in content
    assert "./core/README.md" in content
    assert "./modules/README.md" in content
    assert "./orchestration/README.md" in content
    assert "./orchestration/workflows.md" in content
    assert "../system/api-spec.md" in content
    assert "../system/backend-structure.md" in content
    assert "../system/frontend-structure.md" in content


def test_request_lifecycle_references_runtime_entrypoint() -> None:
    content = _read_text(ARCHITECTURE_DIR / "request-lifecycle.md")

    assert "backend/app/orchestration/builder.py" in content


def test_shared_state_references_state_contract() -> None:
    content = _read_text(ARCHITECTURE_DIR / "shared-state.md")

    assert "backend/app/orchestration/state.py" in content


def test_request_lifecycle_mentions_current_main_workflow_nodes() -> None:
    builder_content = _read_text(ORCHESTRATION_DIR / "builder.py")
    doc_content = _read_text(ARCHITECTURE_DIR / "request-lifecycle.md")

    node_names = sorted(set(re.findall(r'graph\.add_node\("([^"]+)"', builder_content)))

    assert node_names
    missing = [node_name for node_name in node_names if node_name not in doc_content]
    assert missing == []


def test_shared_state_mentions_core_main_workflow_state_keys() -> None:
    content = _read_text(ARCHITECTURE_DIR / "shared-state.md")
    core_keys = (
        "handoff",
        "preprocess_result",
        "rag_result",
        "guideline_result",
        "insight",
        "analysis_plan",
        "analysis_result",
        "visualization_result",
        "merged_context",
        "report_result",
        "output",
        "pending_approval",
    )

    missing = [key for key in core_keys if key not in content]
    assert missing == []


def test_frontend_structure_references_current_workbench_entrypoints() -> None:
    content = _read_text(FRONTEND_STRUCTURE)

    required_refs = (
        "frontend/src/main.tsx",
        "frontend/src/app/App.tsx",
        "frontend/src/app/pages/Workbench.tsx",
        "frontend/src/app/hooks/useAnalysisPipeline.ts",
        "frontend/src/app/hooks/useWorkbenchSessionStore.ts",
        "frontend/src/lib/api.ts",
        "WorkbenchApp.tsx",
    )

    for ref in required_refs:
        assert ref in content


def test_no_nested_docs_prefix_in_architecture_wiki_links() -> None:
    for path in ARCHITECTURE_DIR.rglob("*.md"):
        content = _read_text(path)
        assert "[[docs/architecture/" not in content


def test_no_accidental_nested_docs_directory() -> None:
    assert not (REPO_ROOT / "docs" / "docs").exists()


@pytest.mark.parametrize(
    ("filename", "implementation_refs", "required_terms"),
    [
        (
            "main-workflow.md",
            ("backend/app/orchestration/builder.py",),
            ("intake_flow", "planner", "merge_context", "data_qa_terminal"),
        ),
        (
            "guideline.md",
            ("backend/app/orchestration/workflows/guideline.py",),
            (
                "ensure_guideline_index",
                "retrieve_guideline_context",
                "summarize_guideline_evidence",
            ),
        ),
        (
            "preprocess.md",
            ("backend/app/orchestration/workflows/preprocess.py",),
            (
                "ingestion_and_profile",
                "preprocess_decision",
                "approval_gate",
                "executor",
                "skip",
                "cancel",
            ),
        ),
        (
            "analysis.md",
            ("backend/app/orchestration/workflows/analysis.py",),
            (
                "analysis_planning",
                "analysis_clarification",
                "analysis_execution",
                "analysis_validation",
                "analysis_persist_result",
            ),
        ),
        (
            "rag.md",
            ("backend/app/orchestration/workflows/rag.py",),
            ("ensure_rag_index", "retrieve_context", "insight_synthesis"),
        ),
        (
            "visualization.md",
            ("backend/app/orchestration/workflows/visualization.py",),
            (
                "visualization_planner",
                "approval_gate",
                "visualization_executor",
                "cancel",
            ),
        ),
        (
            "report.md",
            ("backend/app/orchestration/workflows/report.py",),
            (
                "report_draft",
                "approval_gate",
                "finalize",
                "cancel",
            ),
        ),
    ],
)
def test_component_docs_reference_implementation_and_core_nodes(
    filename: str,
    implementation_refs: tuple[str, ...],
    required_terms: tuple[str, ...],
) -> None:
    content = _workflow_contract_content()

    for implementation_ref in implementation_refs:
        assert implementation_ref in content
    for required_term in required_terms:
        assert required_term in content


@pytest.mark.parametrize("filename", sorted(COMPONENT_IMPLEMENTATION_FILES))
def test_component_docs_mention_current_workflow_nodes(filename: str) -> None:
    implementation = COMPONENT_IMPLEMENTATION_FILES[filename]
    implementation_content = _read_text(implementation)
    doc_content = _workflow_contract_content()

    node_names = sorted(set(re.findall(r'graph\.add_node\("([^"]+)"', implementation_content)))

    assert node_names
    missing = [node_name for node_name in node_names if node_name not in doc_content]
    assert missing == []


@pytest.mark.parametrize("filename, status_terms", sorted(COMPONENT_STATUS_TERMS.items()))
def test_component_docs_capture_branch_and_status_contracts(
    filename: str,
    status_terms: tuple[str, ...],
) -> None:
    content = _workflow_contract_content()

    assert "## 하네스 계약" in content
    missing = [term for term in status_terms if term not in content]
    assert missing == []


@pytest.mark.parametrize("filename, payload_terms", sorted(COMPONENT_PAYLOAD_TERMS.items()))
def test_component_docs_capture_payload_contracts(
    filename: str,
    payload_terms: tuple[str, ...],
) -> None:
    content = _workflow_contract_content()

    assert "payload contract" in content
    missing = [term for term in payload_terms if term not in content]
    assert missing == []


@pytest.mark.parametrize("filename, approval_terms", sorted(APPROVAL_COMPONENT_CONTRACTS.items()))
def test_approval_component_docs_capture_resume_contracts(
    filename: str,
    approval_terms: tuple[str, ...],
) -> None:
    content = _workflow_contract_content()

    assert "approval contract" in content
    for approval_term in approval_terms:
        assert approval_term in content
    for decision in ("approve", "revise", "cancel"):
        assert decision in content
