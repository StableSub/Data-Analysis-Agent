from __future__ import annotations

from typing import Any, Mapping


GUIDELINE_REFERENCE_TERMS = (
    "가이드라인",
    "지침",
    "guideline",
)

GUIDELINE_REFERENCE_ACTION_TERMS = (
    "확인",
    "올라온",
    "업로드",
    "파일",
    "내용",
    "기준",
)

GUIDELINE_ANALYSIS_TERMS = (
    "분석",
    "시각화",
    "그래프",
    "차트",
    "막대",
    "추세",
    "비율",
    "불량률",
    "건수",
    "개수",
    "분포",
    "평균",
    "합계",
    "상관",
    "별",
    "analysis",
    "visualize",
    "visualization",
    "graph",
    "chart",
    "count",
    "counts",
    "distribution",
    "rate",
    "ratio",
    "trend",
)


def has_selected_guideline(state: Mapping[str, Any]) -> bool:
    return bool(str(state.get("active_guideline_source_id") or "").strip())


def has_selected_dataset(state: Mapping[str, Any]) -> bool:
    return bool(str(state.get("source_id") or "").strip())


def is_guideline_reference_question(user_input: str) -> bool:
    text = user_input.lower()
    return any(term in text for term in GUIDELINE_REFERENCE_TERMS) and any(
        term in text for term in GUIDELINE_REFERENCE_ACTION_TERMS
    )


def is_selected_guideline_content_question(user_input: str) -> bool:
    text = user_input.lower()
    return any(term in text for term in GUIDELINE_REFERENCE_ACTION_TERMS)


def is_guideline_only_reference_question(user_input: str) -> bool:
    text = user_input.lower()
    return is_guideline_reference_question(text) and not any(
        term in text for term in GUIDELINE_ANALYSIS_TERMS
    )


def route_after_guideline(state: Mapping[str, Any]) -> str:
    if not has_selected_dataset(state):
        return "merge_context"
    if is_guideline_only_reference_question(str(state.get("user_input") or "")):
        return "merge_context"
    return "planner"
