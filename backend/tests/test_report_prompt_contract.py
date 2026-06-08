from __future__ import annotations

from backend.app.modules.reports.ai import PROMPTS
from backend.app.modules.reports.service import _build_deterministic_report_text


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


def test_deterministic_report_fallback_formats_metrics_for_non_experts() -> None:
    report = _build_deterministic_report_text(
        question="전체 품질 현황 리포트를 작성해줘.",
        report_payload={
            "analysis_result": {
                "summary": "양품 2건, 불량 1건입니다.",
                "table": [
                    {"PassOrFail": "Y", "count": 2},
                    {"PassOrFail": "N", "count": 1},
                ],
            },
            "dataset_context": {
                "filename": "mold.csv",
                "row_count_total": 3,
                "column_count": 4,
            },
            "metrics": {
                "raw_metrics": {
                    "pass_count": 2,
                    "defect_count": 1,
                    "defect_rate_pct": 33.33,
                },
                "primary_metrics": {},
                "table_metrics": {
                    "preview_rows": [
                        {"PassOrFail": "Y", "count": 2},
                        {"PassOrFail": "N", "count": 1},
                    ]
                },
            },
        },
    )

    assert "## 주요 지표" in report
    assert "- pass_count: 2" in report
    assert "- defect_rate_pct: 33.33" in report
    assert "| PassOrFail | count |" in report
    assert "| Y | 2 |" in report
    assert "`{" not in report
    assert "표 미리보기:" not in report
