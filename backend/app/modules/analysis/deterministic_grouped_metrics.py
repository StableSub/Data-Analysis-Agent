from __future__ import annotations

from collections.abc import Sequence

from .schemas import AnalysisPlan, FilterCondition, MetricSpec


def build_grouped_metric_code(plan: AnalysisPlan) -> str | None:
    if plan.time_context is not None or plan.expected_output.require_time_axis:
        return None
    if not plan.group_by or not plan.metrics:
        return None
    if any(column not in plan.metadata_snapshot.columns for column in plan.group_by):
        return None
    if any(
        condition.column not in plan.metadata_snapshot.columns
        for condition in plan.filters
    ):
        return None
    if not all(_metric_is_supported(metric, plan) for metric in plan.metrics):
        return None

    filter_lines = _build_filter_lines(plan.filters)
    if filter_lines is None:
        return None

    metric_aliases = [metric.alias for metric in plan.metrics]
    if len(set(metric_aliases)) != len(metric_aliases):
        return None
    if any(alias in plan.group_by for alias in metric_aliases):
        return None

    used_columns = _used_source_columns(
        plan,
        [
            *plan.group_by,
            *(metric.column for metric in plan.metrics),
            *(condition.column for condition in plan.filters),
        ],
    )
    metric_specs = [
        {
            "alias": metric.alias,
            "aggregation": metric.aggregation,
            "column": metric.column,
            "positive_value": metric.positive_value,
        }
        for metric in plan.metrics
    ]

    lines = [
        "work = df.copy()",
        *filter_lines,
        f"group_columns = {plan.group_by!r}",
        f"metric_specs = {metric_specs!r}",
        "rows = []",
        "",
        "def _json_value(value):",
        "    if pd.isna(value):",
        "        return None",
        "    if hasattr(value, 'item'):",
        "        value = value.item()",
        "    if isinstance(value, float) and value.is_integer():",
        "        return int(value)",
        "    return value",
        "",
        "for group_values, group in work.groupby(group_columns, dropna=False, sort=True):",
        "    if len(group_columns) == 1 and not isinstance(group_values, tuple):",
        "        group_values = (group_values,)",
        "    row = {}",
        "    for group_index, group_column in enumerate(group_columns):",
        "        row[group_column] = _json_value(group_values[group_index])",
        "    for metric_index, metric_spec in enumerate(metric_specs):",
        "        alias = metric_spec['alias']",
        "        aggregation = metric_spec['aggregation']",
        "        column = metric_spec.get('column')",
        "        positive_value = metric_spec.get('positive_value')",
        "        if aggregation == 'count':",
        "            if column:",
        "                value = int(group[column].count())",
        "            else:",
        "                value = int(len(group))",
        "        elif aggregation == 'rate':",
        "            numerator = (group[column] == positive_value).sum()",
        "            value = float(numerator / len(group)) if len(group) else 0.0",
        "        else:",
        "            series = pd.to_numeric(group[column], errors='coerce')",
        "            if aggregation == 'sum':",
        "                raw_value = series.sum()",
        "            elif aggregation == 'avg':",
        "                raw_value = series.mean()",
        "            elif aggregation == 'min':",
        "                raw_value = series.min()",
        "            elif aggregation == 'max':",
        "                raw_value = series.max()",
        "            elif aggregation == 'median':",
        "                raw_value = series.median()",
        "            else:",
        "                raw_value = None",
        "            value = _json_value(raw_value)",
        "        row[alias] = value",
        "    rows.append(row)",
        "summary = (",
        "    f\"총 {len(work)}건을 기준으로 {len(group_columns)}개 그룹 축과 \"",
        "    f\"{len(metric_specs)}개 지표를 계산했습니다.\"",
        ")",
        "raw_metrics = {",
        "    'total_count': int(len(work)),",
        "    'group_count': int(len(rows)),",
        f"    'group_columns': {plan.group_by!r},",
        f"    'metric_aliases': {metric_aliases!r},",
        "}",
        "print(json.dumps({",
        "    'summary': summary,",
        "    'table': rows,",
        "    'raw_metrics': raw_metrics,",
        f"    'used_columns': {used_columns!r},",
        "}, ensure_ascii=False))",
    ]
    return "\n".join(lines)


def _metric_is_supported(metric: MetricSpec, plan: AnalysisPlan) -> bool:
    numeric_columns = set(plan.metadata_snapshot.numeric_columns)
    if not metric.alias:
        return False
    if metric.aggregation == "count":
        return metric.column is None or metric.column in plan.metadata_snapshot.columns
    if metric.aggregation == "rate":
        return (
            metric.column in plan.metadata_snapshot.columns
            and metric.positive_value is not None
        )
    return (
        metric.aggregation in {"sum", "avg", "min", "max", "median"}
        and metric.column in plan.metadata_snapshot.columns
        and metric.column in numeric_columns
    )


def _build_filter_lines(filters: Sequence[FilterCondition]) -> list[str] | None:
    lines: list[str] = []
    for condition in filters:
        if condition.operator == "not_null":
            lines.append(
                f"work = work[work[{condition.column!r}].notna()].copy()"
            )
        elif condition.operator == "eq":
            lines.append(
                f"work = work[work[{condition.column!r}] == {condition.value!r}].copy()"
            )
        else:
            return None
    return lines


def _used_source_columns(
    plan: AnalysisPlan,
    candidates: Sequence[str | None],
) -> list[str]:
    available = set(plan.metadata_snapshot.columns)
    columns: list[str] = []
    for column in [*plan.required_columns, *candidates]:
        if column and column in available and column not in columns:
            columns.append(column)
    return columns
