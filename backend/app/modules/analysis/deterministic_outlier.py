from __future__ import annotations

from .schemas import AnalysisPlan, MetricSpec

_OUTLIER_TOKENS = ("outlier", "anomaly", "이상치")


def build_numeric_outlier_code(plan: AnalysisPlan) -> str | None:
    if not _requires_outlier_analysis(plan):
        return None
    target_column = _select_target_column(plan)
    if target_column is None:
        return None

    context_columns = _select_context_columns(plan, target_column)
    metric_pairs = _metric_alias_pairs(plan.metrics)
    used_columns = _used_source_columns(
        plan,
        [target_column, *context_columns, *(column for _, column in metric_pairs)],
    )
    if target_column not in used_columns:
        return None

    lines = [
        "work = df.copy()",
        f"target_column = {target_column!r}",
        f"context_columns = {context_columns!r}",
        f"metric_pairs = {metric_pairs!r}",
        "target_values = pd.to_numeric(work[target_column], errors='coerce')",
        "valid_values = target_values.dropna()",
        "valid_count = int(valid_values.count())",
        "missing_count = int(len(work) - valid_count)",
        "q1 = float(valid_values.quantile(0.25)) if valid_count else None",
        "q3 = float(valid_values.quantile(0.75)) if valid_count else None",
        "iqr = (q3 - q1) if q1 is not None and q3 is not None else None",
        "lower_iqr = float(q1 - 1.5 * iqr) if iqr is not None else None",
        "upper_iqr = float(q3 + 1.5 * iqr) if iqr is not None else None",
        "mean_value = float(valid_values.mean()) if valid_count else None",
        "std_value = float(valid_values.std(ddof=0)) if valid_count else None",
        "lower_sigma = float(mean_value - 3 * std_value) if std_value and std_value > 0 else None",
        "upper_sigma = float(mean_value + 3 * std_value) if std_value and std_value > 0 else None",
        "outlier_mask = pd.Series(False, index=work.index)",
        "if valid_count:",
        "    if lower_iqr is not None and upper_iqr is not None and iqr is not None and iqr > 0:",
        "        outlier_mask = outlier_mask | target_values.lt(lower_iqr) | target_values.gt(upper_iqr)",
        "    if lower_sigma is not None and upper_sigma is not None:",
        "        outlier_mask = outlier_mask | target_values.lt(lower_sigma) | target_values.gt(upper_sigma)",
        "outlier_mask = outlier_mask.fillna(False)",
        "outlier_count = int(outlier_mask.sum())",
        "outlier_rate = float(outlier_count / valid_count) if valid_count else 0.0",
        "",
        "def _json_value(value):",
        "    if pd.isna(value):",
        "        return None",
        "    if isinstance(value, pd.Timestamp):",
        "        return value.isoformat()",
        "    if hasattr(value, 'item'):",
        "        value = value.item()",
        "    if hasattr(value, 'isoformat') and not isinstance(value, str):",
        "        return value.isoformat()",
        "    if isinstance(value, float) and value.is_integer():",
        "        return int(value)",
        "    return value",
        "",
        "rows = []",
        "for row_index, row in work.loc[outlier_mask].head(20).iterrows():",
        "    output_row = {'row_index': int(row_index)}",
        "    for column in context_columns:",
        "        output_row[column] = _json_value(row.get(column))",
        "    output_row[target_column] = _json_value(row.get(target_column))",
        "    output_row['outlier_reason'] = 'iqr_or_3sigma_threshold_exceeded'",
        "    for alias, column in metric_pairs:",
        "        output_row[alias] = _json_value(row.get(column)) if column else None",
        "    rows.append(output_row)",
        "",
        "root_cause_candidates = []",
        "work_with_outlier = work.copy()",
        "work_with_outlier['__outlier'] = outlier_mask",
        "for column in context_columns:",
        "    if column == target_column:",
        "        continue",
        "    grouped = work_with_outlier.groupby(column, dropna=False, sort=True)",
        "    for group_value, group in grouped:",
        "        group_total = int(len(group))",
        "        group_outliers = int(group['__outlier'].sum())",
        "        if group_outliers <= 0:",
        "            continue",
        "        root_cause_candidates.append({",
        "            'column': column,",
        "            'value': _json_value(group_value),",
        "            'outlier_count': group_outliers,",
        "            'total_count': group_total,",
        "            'outlier_rate': float(group_outliers / group_total) if group_total else 0.0,",
        "        })",
        "root_cause_candidates = sorted(",
        "    root_cause_candidates,",
        "    key=lambda item: (item['outlier_count'], item['outlier_rate']),",
        "    reverse=True,",
        ")[:10]",
        "",
        "if valid_count:",
        "    summary = (",
        "        f\"{target_column} 컬럼의 유효값 {valid_count}개 중 \"",
        "        f\"이상치 {outlier_count}개({outlier_rate:.2%})를 확인했습니다. \"",
        "        f\"IQR 및 3시그마 기준을 함께 적용했습니다.\"",
        "    )",
        "else:",
        "    summary = (",
        "        f\"{target_column} 컬럼에서 숫자로 해석 가능한 값이 없어 \"",
        "        \"이상치 개수를 0건으로 보고했습니다. 컬럼 타입과 결측값을 확인해 주세요.\"",
        "    )",
        "raw_metrics = {",
        "    'outliers': {",
        "        'method': 'iqr_or_3sigma',",
        "        'target_column': target_column,",
        "        'valid_count': valid_count,",
        "        'missing_count': missing_count,",
        "        'q1': q1,",
        "        'q3': q3,",
        "        'iqr': iqr,",
        "        'lower_iqr': lower_iqr,",
        "        'upper_iqr': upper_iqr,",
        "        'mean': mean_value,",
        "        'std': std_value,",
        "        'lower_sigma': lower_sigma,",
        "        'upper_sigma': upper_sigma,",
        "        'outlier_count': outlier_count,",
        "        'outlier_rate': outlier_rate,",
        "    },",
        "    'root_cause_candidates': root_cause_candidates,",
        "    'data_quality': {",
        "        'row_count': int(len(work)),",
        "        'valid_numeric_count': valid_count,",
        "        'missing_or_non_numeric_count': missing_count,",
        "    },",
        "}",
        "print(json.dumps({",
        "    'summary': summary,",
        "    'table': rows,",
        "    'raw_metrics': raw_metrics,",
        f"    'used_columns': {used_columns!r},",
        "}, ensure_ascii=False))",
    ]
    return "\n".join(lines)


def _requires_outlier_analysis(plan: AnalysisPlan) -> bool:
    if plan.expected_output.require_outlier_info:
        return True
    haystack = " ".join(
        [
            plan.analysis_type,
            plan.objective,
            *(metric.name for metric in plan.metrics),
            *(metric.alias for metric in plan.metrics),
        ]
    ).lower()
    return any(token in haystack for token in _OUTLIER_TOKENS)


def _select_target_column(plan: AnalysisPlan) -> str | None:
    numeric_columns = set(plan.metadata_snapshot.numeric_columns)
    metric_columns = [
        metric.column
        for metric in plan.metrics
        if metric.column and metric.column in plan.metadata_snapshot.columns
    ]
    for metric in plan.metrics:
        if (
            metric.column
            and metric.column in plan.metadata_snapshot.columns
            and "outlier_target" in f"{metric.name} {metric.alias}".lower()
        ):
            return metric.column
    for column in metric_columns:
        if _column_is_named_in_request(plan, column):
            return column
    for column in metric_columns:
        if column in numeric_columns and _column_is_named_in_request(plan, column):
            return column
    for column in metric_columns:
        if column in numeric_columns:
            return column
    for column in plan.used_columns:
        if column in numeric_columns:
            return column
    return None


def _column_is_named_in_request(plan: AnalysisPlan, column: str) -> bool:
    haystack = f"{plan.analysis_type} {plan.objective}".lower()
    return column.lower() in haystack


def _select_context_columns(plan: AnalysisPlan, target_column: str) -> list[str]:
    candidates = [
        *plan.group_by,
        plan.time_context.time_column if plan.time_context else None,
        *plan.used_columns,
    ]
    context: list[str] = []
    for column in candidates:
        if (
            column
            and column != target_column
            and column in plan.metadata_snapshot.columns
            and column not in context
        ):
            context.append(column)
        if len(context) >= 5:
            break
    return context


def _metric_alias_pairs(metrics: list[MetricSpec]) -> list[tuple[str, str | None]]:
    pairs: list[tuple[str, str | None]] = []
    for metric in metrics:
        if metric.alias and (metric.alias, metric.column) not in pairs:
            pairs.append((metric.alias, metric.column))
    return pairs


def _used_source_columns(
    plan: AnalysisPlan,
    candidates: list[str | None],
) -> list[str]:
    available = set(plan.metadata_snapshot.columns)
    columns: list[str] = []
    for column in [*plan.required_columns, *candidates]:
        if column and column in available and column not in columns:
            columns.append(column)
    return columns
