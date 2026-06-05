from pathlib import Path

from backend.app.modules.eda.ai import PROMPTS
from backend.app.modules.eda.insights import build_deterministic_ai_summary


TECHNICAL_OR_FAILURE_WORDS = (
    "deterministic",
    "LLM",
    "IQR 기준",
    "fallback",
    "자동 요약",
)


def _joined_summary_text(summary: dict[str, str | list[str]]) -> str:
    parts: list[str] = []
    structure_summary = summary["structure_summary"]
    assert isinstance(structure_summary, str)
    parts.append(structure_summary)
    for key in ("quality_issues", "key_insights"):
        values = summary[key]
        assert isinstance(values, list)
        parts.extend(values)
    return "\n".join(parts)


def _assert_no_technical_or_failure_words(text: str) -> None:
    for word in TECHNICAL_OR_FAILURE_WORDS:
        assert word not in text


def test_deterministic_summary_explains_missing_outliers_and_next_actions() -> None:
    summary = build_deterministic_ai_summary(
        {
            "summary": {"row_count": 8, "column_count": 4},
            "quality": {
                "missing_total": 2,
                "missing_ratio": 0.0625,
                "top_missing_columns": [
                    {"column": "revenue", "missing_count": 2, "missing_ratio": 0.25},
                ],
            },
            "stats": {
                "columns": [
                    {"column": "revenue", "mean": 120.0, "min": 20.0, "max": 500.0},
                ],
            },
            "top_correlations": {
                "pairs": [
                    {"column_1": "orders", "column_2": "revenue", "correlation": 0.93},
                ],
            },
            "outliers": {
                "columns": [
                    {"column": "revenue", "outlier_count": 1, "outlier_ratio": 0.125},
                ],
            },
        }
    )

    text = _joined_summary_text(summary)

    assert "총 8행, 4개 컬럼" in summary["structure_summary"]
    assert "먼저" in summary["structure_summary"]
    assert "'revenue' 컬럼" in text
    assert "결측치" in text
    assert "먼저 확인" in text
    assert "함께 움직이는 경향" in text
    assert "입력 오류인지 실제 특이 사례인지 확인" in text
    _assert_no_technical_or_failure_words(text)


def test_deterministic_summary_gives_plain_next_step_for_clean_dataset() -> None:
    summary = build_deterministic_ai_summary(
        {
            "summary": {"row_count": 3, "column_count": 2},
            "quality": {
                "missing_total": 0,
                "missing_ratio": 0.0,
                "top_missing_columns": [],
            },
            "stats": {"columns": []},
            "top_correlations": {"pairs": []},
            "outliers": {"columns": []},
        }
    )

    text = _joined_summary_text(summary)

    assert "눈에 띄는 결측치는 없습니다" in text
    assert "급한 신호는 없습니다" in text
    assert "다음 질문" in text
    _assert_no_technical_or_failure_words(text)


def test_eda_summary_prompt_requires_plain_meaning_and_next_action() -> None:
    prompt = PROMPTS.load_prompt("summary.system")

    for phrase in (
        "쉬운 말",
        "전문 용어",
        "무엇을 의미하는지",
        "다음 행동",
        '"structure_summary"',
        '"quality_issues"',
        '"key_insights"',
        '"guideline_context"',
        '"dataset_overview"',
        '"summary"',
        '"key_points"',
        "나머지 2개 키",
    ):
        assert phrase in prompt
    assert "나머지 3개 키" not in prompt


def test_frontend_mapping_still_consumes_existing_eda_insight_keys() -> None:
    project_root = Path(__file__).resolve().parents[2]
    api_source = (project_root / "frontend/src/lib/api.ts").read_text(encoding="utf-8")
    hook_source = (
        project_root / "frontend/src/app/hooks/useAnalysisPipeline.ts"
    ).read_text(encoding="utf-8")
    workbench_source = (
        project_root / "frontend/src/app/pages/Workbench.tsx"
    ).read_text(encoding="utf-8")

    assert "export interface EdaInsightResponse" in api_source
    assert "structure_summary: string" in api_source
    assert "quality_issues: string[]" in api_source
    assert "key_insights: string[]" in api_source
    assert "dataset_overview?: EdaDatasetOverview | null" in api_source
    assert "insight.structure_summary" in hook_source
    assert "insight.quality_issues" in hook_source
    assert "insight.key_insights" in hook_source
    assert "mapEdaDatasetOverview(insights.dataset_overview)" in hook_source
    assert "fetchEdaInsights(sourceId, guidelineSourceId)" in hook_source
    assert "request.guideline_source_id = requestGuidelineSourceId" in hook_source
    assert "handleSend(value, modelId, selectedGuidelineSourceId)" in workbench_source
    assert "pipeline.startUpload(file, selectedGuidelineSourceId)" in workbench_source
    assert "pipeline.retrySelectedPreEda(selectedGuidelineSourceId)" in workbench_source
