from backend.app.orchestration.error_contract import build_workflow_error, to_public_error


def test_plan_validation_public_error_explains_recovery_action() -> None:
    workflow_error = build_workflow_error(
        stage="plan_validation",
        error_code="planning_failed",
        source="analysis_planning",
        output_type="planning_failed",
        retryable=True,
        diagnostic_message="planner did not route this request to analysis",
    )

    public_error = to_public_error(workflow_error)

    assert public_error["error_code"] == "planning_failed"
    assert public_error["retryable"] is True
    assert "분석 계획" in public_error["error_message"]
    assert any(term in public_error["error_message"] for term in ("분석 목표", "기준 컬럼", "집계 기준"))
    assert any(term in public_error["error_message"] for term in ("전처리", "다시 실행", "지정"))
    assert public_error["error_message"] != "분석 계획을 확인하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    assert "잠시 후 다시 시도" not in public_error["error_message"]
    assert "planner did not route" not in public_error["error_message"]
