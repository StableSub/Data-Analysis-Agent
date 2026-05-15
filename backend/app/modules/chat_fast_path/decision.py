from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal


_FAST_PATH_ELIGIBILITY_THRESHOLD = 0.75

CommonAnalyticsOperation = Literal[
    "basic_metric",
    "correlation",
    "comparison",
    "segment",
    "outlier",
]

_REQUIRED_COLUMN_COUNTS: dict[CommonAnalyticsOperation, int] = {
    "basic_metric": 1,
    "correlation": 2,
    "comparison": 2,
    "segment": 2,
    "outlier": 1,
}

_NUMERIC_METRICS = {
    "mean": ("평균", "average", "mean", "avg"),
    "sum": ("합계", "총합", "sum", "total"),
    "min": ("최소", "최솟값", "minimum", "min"),
    "max": ("최대", "최댓값", "maximum", "max"),
    "median": ("중앙값", "median"),
}
_CATEGORICAL_METRICS = {
    "value_counts": ("빈도", "개수", "건수", "분포", "frequency", "count", "counts"),
    "ratio": ("비율", "구성비", "share", "ratio", "proportion", "percent"),
    "top": ("가장 많은", "최빈", "최다", "top", "most common"),
}
_CORRELATION_KEYWORDS = ("상관", "관계", "correlation", "corr", "relationship", "related")
_COMPARISON_KEYWORDS = ("비교", "compare", "comparison")
_SEGMENT_KEYWORDS = ("별", "그룹", "세그먼트", "segment", "group by", "by ")
_OUTLIER_KEYWORDS = ("이상치", "outlier", "anomaly")
_COMPLEX_BLOCKERS = (
    "왜",
    "원인",
    "이유",
    "전략",
    "추천",
    "제안",
    "예측",
    "모델",
    "리포트",
    "보고서",
    "시각화",
    "차트",
    "그래프",
    "why",
    "cause",
    "reason",
    "strategy",
    "recommend",
    "predict",
    "forecast",
    "model",
    "report",
    "visualize",
    "chart",
    "graph",
)


@dataclass(frozen=True)
class CommonAnalyticsFastPathDecision:
    eligible: bool
    operation: CommonAnalyticsOperation | None = None
    metric: str | None = None
    columns: list[str] = field(default_factory=list)
    eligibility_score: float = 0.0
    blockers: list[str] = field(default_factory=list)

    def to_fast_path_result(self) -> dict[str, Any]:
        return {
            "status": "handled" if self.eligible else "skipped",
            "kind": "common_analytics",
            "operation": self.operation or "",
            "metric": self.metric or "",
            "columns": self.columns,
            "eligibility_score": self.eligibility_score,
            "blockers": self.blockers,
        }


def decide_common_analytics_fast_path(
    question: str,
    dataset_context: Mapping[str, Any],
) -> CommonAnalyticsFastPathDecision:
    normalized_question = _normalize_question(question)
    if not normalized_question:
        return _ineligible("empty_question")
    if dataset_context.get("available") is not True:
        return _ineligible("dataset_context_unavailable")

    blockers = _detect_complex_blockers(normalized_question)
    operation = _detect_operation(normalized_question)
    metric = _detect_metric(normalized_question, operation)
    matched_columns = _match_columns(normalized_question, dataset_context)

    if operation is None:
        blockers.append("unsupported_operation")
    if operation is not None:
        required_column_count = _REQUIRED_COLUMN_COUNTS[operation]
        if len(matched_columns) < required_column_count:
            blockers.append("missing_column_hint")
        elif len(matched_columns) > required_column_count:
            blockers.append("ambiguous_column_hint")
    if operation == "basic_metric" and metric is None:
        blockers.append("missing_metric_hint")
    if operation is not None and _has_type_blocker(
        operation=operation,
        metric=metric,
        columns=matched_columns,
        dataset_context=dataset_context,
    ):
        blockers.append("column_type_mismatch")

    eligibility_score = _score_decision(
        operation=operation,
        metric=metric,
        columns=matched_columns,
        blockers=blockers,
    )
    eligible = (
        operation is not None
        and len(blockers) == 0
        and eligibility_score >= _FAST_PATH_ELIGIBILITY_THRESHOLD
    )
    return CommonAnalyticsFastPathDecision(
        eligible=eligible,
        operation=operation,
        metric=metric,
        columns=matched_columns,
        eligibility_score=eligibility_score,
        blockers=blockers,
    )


def _ineligible(blocker: str) -> CommonAnalyticsFastPathDecision:
    return CommonAnalyticsFastPathDecision(
        eligible=False,
        eligibility_score=0.0,
        blockers=[blocker],
    )


def _normalize_question(question: str) -> str:
    return " ".join(str(question or "").strip().lower().split())


def _detect_complex_blockers(question: str) -> list[str]:
    blockers: list[str] = []
    if any(_keyword_mentioned(question=question, keyword=keyword) for keyword in _COMPLEX_BLOCKERS):
        blockers.append("complex_request")
    if question.count("?") > 1 or question.count("？") > 1:
        blockers.append("multi_question")
    return blockers


def _keyword_mentioned(*, question: str, keyword: str) -> bool:
    normalized_keyword = _normalize_column(keyword)
    if not normalized_keyword:
        return False
    if _is_ascii_identifier(normalized_keyword):
        pattern = rf"(?<![a-z0-9_]){re.escape(normalized_keyword)}(?=$|[\s?.!,])"
        return re.search(pattern, _normalize_column(question)) is not None
    return normalized_keyword in _normalize_column(question)


def _detect_operation(question: str) -> CommonAnalyticsOperation | None:
    if any(keyword in question for keyword in _CORRELATION_KEYWORDS):
        return "correlation"
    if any(keyword in question for keyword in _OUTLIER_KEYWORDS):
        return "outlier"
    if any(keyword in question for keyword in _COMPARISON_KEYWORDS):
        return "comparison"
    if any(keyword in question for keyword in _SEGMENT_KEYWORDS):
        return "segment"
    if _detect_metric(question, "basic_metric") is not None:
        return "basic_metric"
    return None


def _detect_metric(
    question: str,
    operation: CommonAnalyticsOperation | None,
) -> str | None:
    if operation == "correlation":
        return "correlation"
    if operation == "outlier":
        return "outlier"
    if operation in {"comparison", "segment"}:
        for metric, keywords in _NUMERIC_METRICS.items():
            if any(keyword in question for keyword in keywords):
                return metric
        return "mean"

    for metric, keywords in {**_NUMERIC_METRICS, **_CATEGORICAL_METRICS}.items():
        if any(keyword in question for keyword in keywords):
            return metric
    return None


def _match_columns(question: str, dataset_context: Mapping[str, Any]) -> list[str]:
    columns = _as_text_list(dataset_context.get("columns"))
    column_aliases = _as_alias_mapping(dataset_context.get("column_aliases"))
    column_value_samples = _as_alias_mapping(dataset_context.get("column_value_samples"))
    matched = [
        column
        for column in columns
        if _column_mentioned(
            question=question,
            column=column,
            aliases=[
                *column_aliases.get(column, []),
                *column_value_samples.get(column, []),
            ],
        )
    ]
    return matched


def _column_mentioned(*, question: str, column: str, aliases: list[str]) -> bool:
    normalized_column = _normalize_column(column)
    if not normalized_column:
        return False
    if any(_alias_mentioned(question=question, alias=alias) for alias in aliases):
        return True
    if any(_alias_mentioned(question=question, alias=variant) for variant in _column_name_variants(column)):
        return True
    if _is_ascii_identifier(normalized_column):
        pattern = rf"(?<![a-z0-9_]){re.escape(normalized_column)}(?![a-z0-9_])"
        return re.search(pattern, _normalize_column(question)) is not None
    compact_question = _normalize_column(question)
    compact_column = normalized_column.replace(" ", "")
    return normalized_column in question or compact_column in compact_question


def _normalize_column(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _alias_mentioned(*, question: str, alias: str) -> bool:
    normalized_alias = _normalize_column(alias)
    if not normalized_alias:
        return False
    if _is_ascii_identifier(normalized_alias):
        pattern = rf"(?<![a-z0-9_]){re.escape(normalized_alias)}(?![a-z0-9_])"
        return re.search(pattern, _normalize_column(question)) is not None
    compact_question = _normalize_column(question).replace(" ", "")
    compact_alias = normalized_alias.replace(" ", "")
    return normalized_alias in question or compact_alias in compact_question


def _column_name_variants(column: str) -> list[str]:
    variants = [column, re.sub(r"\([^)]*\)", "", column)]
    normalized_variants = []
    seen = set()
    for variant in variants:
        normalized = _normalize_column(variant)
        alnum = re.sub(r"[^a-z0-9가-힣]+", " ", normalized).strip()
        for candidate in (normalized, alnum, alnum.replace(" ", "_")):
            text = candidate.strip()
            if text and text not in seen:
                seen.add(text)
                normalized_variants.append(text)
    return normalized_variants


def _is_ascii_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_ ]*", value))


def _has_type_blocker(
    *,
    operation: CommonAnalyticsOperation,
    metric: str | None,
    columns: list[str],
    dataset_context: Mapping[str, Any],
) -> bool:
    numeric_columns = set(_as_text_list(dataset_context.get("numeric_columns")))
    categorical_columns = set(_as_text_list(dataset_context.get("categorical_columns")))
    group_key_columns = set(_as_text_list(dataset_context.get("group_key_columns")))

    if operation in {"correlation", "outlier"}:
        return any(column not in numeric_columns for column in columns)
    if operation == "basic_metric":
        if metric in _NUMERIC_METRICS:
            return any(column not in numeric_columns for column in columns)
        if metric in _CATEGORICAL_METRICS:
            return any(
                column not in categorical_columns and column not in group_key_columns
                for column in columns
            )
    if operation in {"comparison", "segment"} and len(columns) >= 2:
        metric_columns = [column for column in columns if column in numeric_columns]
        group_columns = [
            column
            for column in columns
            if column in categorical_columns or column in group_key_columns
        ]
        return not metric_columns or not group_columns
    return False


def _score_decision(
    *,
    operation: CommonAnalyticsOperation | None,
    metric: str | None,
    columns: list[str],
    blockers: list[str],
) -> float:
    score = 0.0
    if operation is not None:
        score += 0.35
    if metric is not None:
        score += 0.2
    if operation is not None and len(columns) >= _REQUIRED_COLUMN_COUNTS[operation]:
        score += 0.35
    if not blockers:
        score += 0.1
    else:
        score -= 0.35
    return round(max(score, 0.0), 2)


def _as_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item or "").strip())]


def _as_alias_mapping(value: object) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        return {}
    aliases_by_column: dict[str, list[str]] = {}
    for column, aliases in value.items():
        column_text = str(column or "").strip()
        if column_text and isinstance(aliases, list):
            aliases_by_column[column_text] = _as_text_list(aliases)
    return aliases_by_column
