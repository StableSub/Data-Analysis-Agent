from pathlib import Path


def test_workbench_planning_error_guidance_targets_plan_recovery() -> None:
    project_root = Path(__file__).resolve().parents[2]
    source = (project_root / "frontend/src/app/pages/Workbench.tsx").read_text()

    assert "plan_validation" in source
    assert "planning_failed" in source
    assert "분석 계획 오류 해결" in source
    assert "지표와 기준 컬럼 지정" in source
    assert "답 가능한 질문 추천" in source
    assert "다시 시도하기 전에 선택하세요" in source
