from __future__ import annotations

from backend.app.modules.reports.ai import PROMPTS


def test_report_draft_prompt_defines_markdown_report_section_contract() -> None:
    prompt = PROMPTS.load_prompt("draft.system")

    expected_sections = [
        "# {보고서 제목}",
        "## 분석 목적",
        "## 데이터 개요",
        "## 핵심 요약",
        "## 주요 지표",
        "## 분석 결과",
        "## 시각화 해석",
        "## 참고 근거",
        "## 한계 및 주의사항",
        "## 권고사항",
    ]

    positions = [prompt.index(section) for section in expected_sections]
    assert positions == sorted(positions)
    assert "필수 섹션" in prompt
    assert "선택 섹션" in prompt
    assert "시각화 해석" in prompt
    assert "참고 근거" in prompt
    assert "생성된 시각화 없음" in prompt


def test_report_draft_prompt_defines_grounding_and_revision_rules() -> None:
    prompt = PROMPTS.load_prompt("draft.system")

    assert "숫자" in prompt
    assert "파일명" in prompt
    assert "컬럼명" in prompt
    assert "인과" in prompt
    assert "table preview" in prompt
    assert "전체 통계" in prompt
    assert "row_count_total" in prompt
    assert "column_count" in prompt
    assert "0" in prompt
    assert "generated" in prompt
    assert "수정 요청" in prompt
    assert "섹션 계약" in prompt
    assert "최대 3개" in prompt
    assert "내부 workflow" in prompt


def test_report_draft_prompt_no_longer_limits_report_to_three_sections() -> None:
    prompt = PROMPTS.load_prompt("draft.system")

    assert "반드시 아래 3개 섹션 제목으로만" not in prompt
    assert "요약\n핵심 인사이트\n권고사항" not in prompt
