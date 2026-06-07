from pathlib import Path


def test_workbench_analysis_repair_failure_guidance_targets_question_repair() -> None:
    project_root = Path(__file__).resolve().parents[2]
    source = (project_root / "frontend/src/app/pages/Workbench.tsx").read_text()

    assert "analysis_repair_failed" in source
    assert "analysis_failed" in source
    assert "분석 실행 오류 해결" in source
    assert "자동 코드 수정으로도 실행 가능한 분석을 만들지 못했습니다" in source
    assert "질문 범위 좁히기" in source
    assert "기준 컬럼 다시 선택" in source
    assert "원본 데이터 상태 확인" in source
