import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_PATH = PROJECT_ROOT / "frontend/src/app/hooks/useAnalysisPipeline.ts"
WORKBENCH_PATH = PROJECT_ROOT / "frontend/src/app/pages/Workbench.tsx"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_callback_body(source: str, name: str) -> str:
    marker = f"const {name} = useCallback"
    start = source.find(marker)
    assert start >= 0, f"{name} callback not found"
    open_brace = source.find("{", start)
    assert open_brace >= 0, f"{name} callback body not found"

    depth = 0
    for index in range(open_brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace + 1:index]
    raise AssertionError(f"{name} callback body is not balanced")


def test_error_transition_clears_stale_pending_approval() -> None:
    pipeline_source = _source(PIPELINE_PATH)
    body = _extract_callback_body(pipeline_source, "transitionToError")

    assert "setPendingApproval(null)" in body


def test_resume_run_consumes_approval_before_streaming_result() -> None:
    pipeline_source = _source(PIPELINE_PATH)
    body = _extract_callback_body(pipeline_source, "resumeRun")

    clear_index = body.find("setPendingApproval(null)")
    request_index = body.find("const request = {")

    assert clear_index >= 0
    assert request_index >= 0
    assert clear_index < request_index


def test_error_state_does_not_leave_question_submit_blocked_by_stale_approval() -> None:
    pipeline_source = _source(PIPELINE_PATH)
    body = _extract_callback_body(pipeline_source, "handleSend")

    assert "if (!question || pendingApproval || applyingPreEdaSourceId !== null) return;" not in body
    assert re.search(r"pendingApproval\s*&&\s*state\s*===\s*[\"']needs-user[\"']", body)


def test_failed_analysis_snapshot_is_navigable_without_marking_completed() -> None:
    workbench_source = _source(WORKBENCH_PATH)

    assert "const hasAnalysisSnapshot" in workbench_source
    assert "completed: hasCompletedAnalysis" in workbench_source
    assert "onNavigate: hasAnalysisSnapshot" in workbench_source
    assert "`${step.label} 오류 보기`" in workbench_source
