from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Final


_QUOTED_IDENTIFIER_RE: Final = re.compile(r"[`'\"]([^`'\"]+)[`'\"]")
_COLUMN_SUFFIX_RE: Final = re.compile(
    r"(?:^|[\s,.;:()\[\]{}])([A-Za-z0-9_가-힣][A-Za-z0-9_가-힣.-]{0,80})\s*컬럼"
)
_TECHNICAL_IDENTIFIER_RE: Final = re.compile(
    r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b"
)
_NON_IDENTIFIER_RE: Final = re.compile(r"[^0-9A-Za-z가-힣]+")
_TECHNICAL_TOKEN_MARKER_RE: Final = re.compile(r"[_0-9A-Z]")
_MAX_SUGGESTIONS: Final = 8
_ANALYSIS_INTENT_TERMS: Final = (
    "분석",
    "상관",
    "관련성",
    "관계",
    "비교",
    "영향",
    "불량",
    "양품",
    "이상치",
    "집계",
    "평균",
    "합계",
    "건수",
    "비율",
    "추세",
    "correlation",
    "relationship",
    "compare",
    "impact",
    "effect",
    "outlier",
    "anomaly",
    "average",
    "count",
    "ratio",
    "trend",
)
_PREPROCESS_INTENT_TERMS: Final = (
    "전처리",
    "결측",
    "결측치",
    "정규화",
    "표준화",
    "스케일",
    "scale",
    "normalize",
    "standardize",
    "인코딩",
    "형변환",
    "파생",
    "컬럼명",
)
_GENERIC_COLUMN_REFERENCES: Final = frozenset(
    {
        "수치형",
        "숫자형",
        "범주형",
        "문자형",
        "문자열",
        "날짜형",
        "시간형",
        "결측",
        "결측치",
        "전체",
        "모든",
        "numeric",
        "number",
        "categorical",
        "category",
        "string",
        "text",
        "datetime",
        "date",
        "time",
    }
)


@dataclass(frozen=True, slots=True)
class ExplicitColumnIssue:
    missing_column: str
    related_columns: tuple[str, ...]
    available_columns: tuple[str, ...]

    def clarification_message(self) -> str:
        if self.related_columns:
            related = ", ".join(self.related_columns)
            return (
                f"현재 데이터에는 `{self.missing_column}` 컬럼이 없습니다. "
                f"관련 컬럼으로는 {related}가 있습니다. "
                "이 중 사용할 컬럼을 지정하거나 실제 컬럼명으로 다시 질문해 주세요."
            )

        available = ", ".join(self.available_columns)
        return (
            f"현재 데이터에는 `{self.missing_column}` 컬럼이 없습니다. "
            f"사용 가능한 컬럼 예시: {available}. "
            "분석에 사용할 실제 컬럼명을 지정해 주세요."
        )


def find_explicit_column_issue(
    question: str,
    columns: Sequence[str],
) -> ExplicitColumnIssue | None:
    if not columns:
        return None

    for candidate in _extract_explicit_references(question):
        if _is_generic_column_reference(candidate):
            continue
        if _has_available_column(candidate, columns):
            continue
        return ExplicitColumnIssue(
            missing_column=candidate,
            related_columns=_related_columns(candidate, columns),
            available_columns=tuple(columns[:_MAX_SUGGESTIONS]),
        )
    return None


def should_preflight_explicit_column_issue(user_input: str) -> bool:
    text = str(user_input or "").lower()
    return any(term in text for term in _ANALYSIS_INTENT_TERMS) and not any(
        term in text for term in _PREPROCESS_INTENT_TERMS
    )


def _extract_explicit_references(question: str) -> tuple[str, ...]:
    text = str(question or "")
    candidates: list[str] = []
    candidates.extend(
        match.group(1).strip() for match in _QUOTED_IDENTIFIER_RE.finditer(text)
    )
    candidates.extend(
        candidate
        for match in _COLUMN_SUFFIX_RE.finditer(text)
        if (candidate := match.group(1).strip())
        and _looks_like_technical_column_token(candidate)
    )
    candidates.extend(
        match.group(0).strip()
        for match in _TECHNICAL_IDENTIFIER_RE.finditer(text)
    )
    return _dedupe_nonempty(candidates)


def _has_available_column(candidate: str, columns: Sequence[str]) -> bool:
    by_exact = set(columns)
    by_lower = {column.lower() for column in columns}
    by_loose = {_normalize_identifier(column) for column in columns}
    return (
        candidate in by_exact
        or candidate.lower() in by_lower
        or _normalize_identifier(candidate) in by_loose
    )


def _related_columns(candidate: str, columns: Sequence[str]) -> tuple[str, ...]:
    lower_prefix = f"{candidate.lower()}_"
    loose_prefix = _normalize_identifier(candidate)
    related: list[str] = []
    for column in columns:
        lower_column = column.lower()
        loose_column = _normalize_identifier(column)
        if lower_column.startswith(lower_prefix) or (
            loose_prefix and loose_column.startswith(loose_prefix)
        ):
            related.append(column)
        if len(related) >= _MAX_SUGGESTIONS:
            break
    return tuple(related)


def _normalize_identifier(value: str) -> str:
    return _NON_IDENTIFIER_RE.sub("", value).lower()


def _is_generic_column_reference(candidate: str) -> bool:
    return _normalize_identifier(candidate) in _GENERIC_COLUMN_REFERENCES


def _looks_like_technical_column_token(candidate: str) -> bool:
    return bool(_TECHNICAL_TOKEN_MARKER_RE.search(candidate))


def _dedupe_nonempty(candidates: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for candidate in candidates:
        stripped = candidate.strip()
        normalized = _normalize_identifier(stripped)
        if not stripped or normalized in seen:
            continue
        seen.add(normalized)
        result.append(stripped)
    return tuple(result)
