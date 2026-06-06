from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from ..datasets.service import DatasetReader
from .decision import CommonAnalyticsFastPathDecision
from .label_distribution import (
    counts_table,
    pass_or_fail_metrics,
    pass_or_fail_summary,
    serialize_value,
)


_TOP_N = 5
_ROUND_DIGITS = 4


@dataclass(frozen=True)
class CommonAnalyticsExecutionResult:
    operation: str
    metric: str
    columns: list[str]
    summary: str
    value: Any | None = None
    table: list[dict[str, Any]] = field(default_factory=list)
    raw_metrics: dict[str, Any] = field(default_factory=dict)


def execute_common_analytics(
    *,
    decision: CommonAnalyticsFastPathDecision,
    storage_path: str,
    dataset_context: Mapping[str, Any],
    reader: DatasetReader,
) -> CommonAnalyticsExecutionResult:
    if not decision.eligible:
        raise ValueError("common analytics fast path decision is not eligible")
    if decision.operation is None:
        raise ValueError("common analytics operation is required")
    if decision.metric is None:
        raise ValueError("common analytics metric is required")
    if not decision.columns:
        raise ValueError("common analytics columns are required")

    df = reader.read_csv(storage_path, usecols=decision.columns)
    if decision.operation == "basic_metric":
        return _execute_basic_metric(df=df, decision=decision)
    if decision.operation == "correlation":
        return _execute_correlation(df=df, decision=decision)
    if decision.operation in {"comparison", "segment"}:
        return _execute_group_metric(
            df=df,
            decision=decision,
            dataset_context=dataset_context,
        )
    if decision.operation == "outlier":
        return _execute_outlier(df=df, decision=decision)
    raise ValueError(f"unsupported common analytics operation: {decision.operation}")


def _execute_basic_metric(
    *,
    df: pd.DataFrame,
    decision: CommonAnalyticsFastPathDecision,
) -> CommonAnalyticsExecutionResult:
    column = decision.columns[0]
    metric = str(decision.metric or "")
    series = df[column]

    if metric in {"mean", "sum", "min", "max", "median"}:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        value = _numeric_metric(numeric, metric)
        return CommonAnalyticsExecutionResult(
            operation="basic_metric",
            metric=metric,
            columns=[column],
            summary=f"{column} {metric} = {_format_number(value)}",
            value=value,
            raw_metrics={
                "column": column,
                "metric": metric,
                "value": value,
                "non_null_count": int(numeric.shape[0]),
            },
        )

    counts = series.dropna().value_counts()
    total = int(counts.sum())
    table = counts_table(counts, total=total, top_n=_TOP_N)
    if metric == "top":
        top_row = table[0] if table else {}
        return CommonAnalyticsExecutionResult(
            operation="basic_metric",
            metric=metric,
            columns=[column],
            summary=f"{column} 최빈값 = {top_row.get('value', '')}",
            value=top_row.get("value"),
            table=table,
            raw_metrics={"column": column, "metric": metric, "total": total},
        )

    raw_metrics: dict[str, Any] = {"column": column, "metric": metric, "total": total}
    label_metrics = pass_or_fail_metrics(column=column, table=table, total=total)
    summary = f"{column} {metric} calculated for top {min(len(table), _TOP_N)} values"
    if label_metrics is not None:
        raw_metrics.update(label_metrics)
        table = _with_labeled_value_column(column=column, table=table)
        summary = pass_or_fail_summary(label_metrics)

    return CommonAnalyticsExecutionResult(
        operation="basic_metric",
        metric=metric,
        columns=[column],
        summary=summary,
        table=table,
        raw_metrics=raw_metrics,
    )


def _execute_correlation(
    *,
    df: pd.DataFrame,
    decision: CommonAnalyticsFastPathDecision,
) -> CommonAnalyticsExecutionResult:
    left, right = decision.columns[:2]
    pair = df[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
    value = _round_float(pair[left].corr(pair[right])) if not pair.empty else None
    return CommonAnalyticsExecutionResult(
        operation="correlation",
        metric="correlation",
        columns=[left, right],
        summary=f"{left}와 {right}의 상관계수 = {_format_number(value)}",
        value=value,
        raw_metrics={
            "left_column": left,
            "right_column": right,
            "correlation": value,
            "non_null_pair_count": int(pair.shape[0]),
        },
    )


def _execute_group_metric(
    *,
    df: pd.DataFrame,
    decision: CommonAnalyticsFastPathDecision,
    dataset_context: Mapping[str, Any],
) -> CommonAnalyticsExecutionResult:
    metric = str(decision.metric or "mean")
    group_column, metric_column = _resolve_group_metric_columns(
        columns=decision.columns,
        dataset_context=dataset_context,
    )
    working = df[[group_column, metric_column]].copy()
    working[metric_column] = pd.to_numeric(working[metric_column], errors="coerce")
    grouped = working.dropna(subset=[group_column, metric_column]).groupby(group_column)[metric_column]
    values = _apply_group_metric(grouped, metric)
    table = [
        {
            "group": serialize_value(group),
            metric: _round_float(value),
        }
        for group, value in values.sort_values(ascending=False).head(_TOP_N).items()
    ]
    return CommonAnalyticsExecutionResult(
        operation=str(decision.operation),
        metric=metric,
        columns=[group_column, metric_column],
        summary=f"{group_column}별 {metric_column} {metric} calculated",
        table=table,
        raw_metrics={
            "group_column": group_column,
            "metric_column": metric_column,
            "metric": metric,
            "group_count": int(values.shape[0]),
        },
    )


def _execute_outlier(
    *,
    df: pd.DataFrame,
    decision: CommonAnalyticsFastPathDecision,
) -> CommonAnalyticsExecutionResult:
    column = decision.columns[0]
    numeric = pd.to_numeric(df[column], errors="coerce").dropna()
    q1 = _round_float(numeric.quantile(0.25)) if not numeric.empty else None
    q3 = _round_float(numeric.quantile(0.75)) if not numeric.empty else None
    iqr = _round_float(q3 - q1) if q1 is not None and q3 is not None else None
    lower_bound = _round_float(q1 - 1.5 * iqr) if q1 is not None and iqr is not None else None
    upper_bound = _round_float(q3 + 1.5 * iqr) if q3 is not None and iqr is not None else None
    outliers = numeric[(numeric < lower_bound) | (numeric > upper_bound)] if lower_bound is not None and upper_bound is not None else numeric.iloc[0:0]
    outlier_count = int(outliers.shape[0])
    return CommonAnalyticsExecutionResult(
        operation="outlier",
        metric="outlier",
        columns=[column],
        summary=f"{column} 이상치 {outlier_count}개",
        value=outlier_count,
        raw_metrics={
            "column": column,
            "q1": q1,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "outlier_count": outlier_count,
            "non_null_count": int(numeric.shape[0]),
        },
    )


def _numeric_metric(series: pd.Series, metric: str) -> float | None:
    if series.empty:
        return None
    if metric == "mean":
        return _round_float(series.mean())
    if metric == "sum":
        return _round_float(series.sum())
    if metric == "min":
        return _round_float(series.min())
    if metric == "max":
        return _round_float(series.max())
    if metric == "median":
        return _round_float(series.median())
    raise ValueError(f"unsupported numeric metric: {metric}")


def _resolve_group_metric_columns(
    *,
    columns: list[str],
    dataset_context: Mapping[str, Any],
) -> tuple[str, str]:
    numeric_columns = set(_as_text_list(dataset_context.get("numeric_columns")))
    categorical_columns = set(_as_text_list(dataset_context.get("categorical_columns")))
    group_key_columns = set(_as_text_list(dataset_context.get("group_key_columns")))

    metric_columns = [column for column in columns if column in numeric_columns]
    group_columns = [
        column
        for column in columns
        if column in categorical_columns or column in group_key_columns
    ]
    if not metric_columns or not group_columns:
        raise ValueError("group metric requires one group column and one numeric column")
    return group_columns[0], metric_columns[0]


def _apply_group_metric(grouped: Any, metric: str) -> pd.Series:
    if metric == "sum":
        return grouped.sum()
    if metric == "min":
        return grouped.min()
    if metric == "max":
        return grouped.max()
    if metric == "median":
        return grouped.median()
    return grouped.mean()


def _with_labeled_value_column(
    *,
    column: str,
    table: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            column: row.get("value"),
            **row,
        }
        for row in table
    ]


def _round_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), _ROUND_DIGITS)


def _format_number(value: object) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _as_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := str(item or "").strip())]
