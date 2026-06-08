import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_PATH = PROJECT_ROOT / "frontend/src/lib/api.ts"
PIPELINE_PATH = PROJECT_ROOT / "frontend/src/app/hooks/useAnalysisPipeline.ts"
WORKBENCH_PATH = PROJECT_ROOT / "frontend/src/app/pages/Workbench.tsx"
ASSISTANT_REPORT_PATH = (
    PROJECT_ROOT / "frontend/src/app/components/genui/AssistantReportMessage.tsx"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_callback_body(source: str, name: str) -> str:
    marker = f"const {name} = useCallback"
    return _extract_balanced_body(source, marker, f"{name} callback")


def _extract_function_body(source: str, name: str) -> str:
    marker = f"const {name} = ("
    return _extract_balanced_body(source, marker, f"{name} function")


def _extract_balanced_body(source: str, marker: str, label: str) -> str:
    start = source.find(marker)
    assert start >= 0, f"{label} not found"
    open_brace = source.find("{", start)
    assert open_brace >= 0, f"{label} body not found"

    depth = 0
    for index in range(open_brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace + 1:index]
    raise AssertionError(f"{label} body is not balanced")


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


def test_clarification_guidance_teaches_query_rewrite_instead_of_running_next_query() -> None:
    workbench_source = _source(WORKBENCH_PATH)
    guidance_body = _extract_function_body(workbench_source, "buildRepairGuidance")

    stale_executable_suggestions = [
        "질문을 조금 더 구체화하세요",
        "분석 기준이나 대상 컬럼을 지정하면 바로 다음 실행으로 이어집니다.",
        "그룹 기준으로 좁히기",
        "결측치부터 확인",
        "질문 다시 쓰기",
        "분석 질문 3개를 추천해줘",
    ]
    for stale_text in stale_executable_suggestions:
        assert stale_text not in guidance_body

    assert "좋은 분석 질문으로 바꾸는 방법" in guidance_body
    assert "무엇을 계산할지 쓰기" in guidance_body
    assert "대상 컬럼과 기준을 함께 쓰기" in guidance_body
    assert "실제 컬럼명 그대로 쓰기" in guidance_body
    assert "오류를 피하려면" in guidance_body


def test_repair_guidance_supports_passive_feedback_items_without_prompt_submission() -> None:
    assistant_source = _source(ASSISTANT_REPORT_PATH)

    assert "prompt?: string;" in assistant_source
    assert "const canRunAction = Boolean(action.prompt && onRepairAction)" in assistant_source
    assert "onClick={() => onRepairAction?.(action.prompt)}" not in assistant_source


def test_frontend_prefers_backend_query_feedback_over_template_guidance() -> None:
    api_source = _source(API_PATH)
    pipeline_source = _source(PIPELINE_PATH)
    workbench_source = _source(WORKBENCH_PATH)
    guidance_body = _extract_function_body(workbench_source, "buildRepairGuidance")

    assert "export interface QueryFeedbackPayload" in api_source
    assert "query_feedback?: QueryFeedbackPayload;" in api_source
    assert "query_feedback:" in pipeline_source

    backend_feedback_index = guidance_body.find("const backendFeedback = response?.query_feedback")
    template_metric_index = guidance_body.find("const metric =")
    assert backend_feedback_index >= 0
    assert template_metric_index >= 0
    assert backend_feedback_index < template_metric_index
    assert "return backendFeedback;" in guidance_body


def test_preprocess_approval_surfaces_nonexpert_guidance_fields() -> None:
    api_source = _source(API_PATH)
    pipeline_source = _source(PIPELINE_PATH)
    workbench_source = _source(WORKBENCH_PATH)

    assert "why_this_matters" in api_source
    assert "expected_impact" in api_source
    assert "skip_risk" in api_source

    assert "guidance:" in pipeline_source
    assert "why_this_matters" in pipeline_source
    assert "expected_impact" in pipeline_source
    assert "skip_risk" in pipeline_source

    pending_changes_body = _extract_function_body(workbench_source, "buildPendingApprovalChanges")
    assert "왜 중요한가" in pending_changes_body
    assert "예상 효과" in pending_changes_body
    assert "건너뛰면" in pending_changes_body

    pending_preview_body = _extract_function_body(workbench_source, "buildPendingApprovalPreview")
    assert "why_this_matters" in pending_preview_body
