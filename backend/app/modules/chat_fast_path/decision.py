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
_CORRELATION_KEYWORDS = ("상관", "correlation", "corr")
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
    if operation is not None and len(matched_columns) < _REQUIRED_COLUMN_COUNTS[operation]:
        blockers.append("missing_column_hint")
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
    if any(keyword in question for keyword in _COMPLEX_BLOCKERS):
        blockers.append("complex_request")
    if question.count("?") > 1 or question.count("？") > 1:
        blockers.append("multi_question")
    return blockers


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
    matched = [
        column
        for column in columns
        if _column_mentioned(question=question, column=column)
    ]
    return matched


def _column_mentioned(*, question: str, column: str) -> bool:
    normalized_column = _normalize_column(column)
    if not normalized_column:
        return False
    if _is_ascii_identifier(normalized_column):
        pattern = rf"(?<![a-z0-9_]){re.escape(normalized_column)}(?![a-z0-9_])"
        return re.search(pattern, question) is not None
    compact_question = _normalize_column(question)
    compact_column = normalized_column.replace(" ", "")
    return normalized_column in question or compact_column in compact_question


def _normalize_column(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


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
    return round(score, 2)


def _as_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item or "").strip())]
