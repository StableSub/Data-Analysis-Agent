from __future__ import annotations

from collections.abc import Sequence

from .schemas import AnalysisPlan

_ONE_HOT_PREFIXES = {
    "PART_NO": "PART_NO_",
    "PART_NAME": "PART_NAME_",
    "Reason": "Reason_",
    "EQUIP_CD": "EQUIP_CD_",
    "EQUIP_NAME": "EQUIP_NAME_",
}
_QUALITY_TERMS = (
    "quality_status_summary",
    "quality",
    "품질",
    "양품",
)


def build_quality_status_summary_code(plan: AnalysisPlan) -> str | None:
    if not _is_quality_summary_plan(plan):
        return None

    pass_column = "PassOrFail" if "PassOrFail" in plan.metadata_snapshot.columns else None
    part_no_columns = _one_hot_columns(plan, "PART_NO")
    part_name_columns = _one_hot_columns(plan, "PART_NAME")
    reason_columns = _one_hot_columns(plan, "Reason")
    quality_columns = [
        pass_column,
        *part_no_columns,
        *part_name_columns,
        *reason_columns,
    ]
    if not any(quality_columns):
        return None
    used_columns = _ordered_existing_columns(
        plan,
        quality_columns,
    )

    return "\n".join(
        [
            f"pass_column = {pass_column!r}",
            f"part_no_columns = {part_no_columns!r}",
            f"part_name_columns = {part_name_columns!r}",
            f"reason_columns = {reason_columns!r}",
            f"used_columns = {used_columns!r}",
            "total_count = int(len(df))",
            "rows = []",
            "warnings = []",
            "",
            "def _json_label(value):",
            "    if pd.isna(value):",
            "        return 'missing'",
            "    if isinstance(value, float) and value.is_integer():",
            "        return str(int(value))",
            "    return str(value)",
            "",
            "def _active_count(column):",
            "    values = pd.to_numeric(df[column], errors='coerce').fillna(0)",
            "    return int((values > 0).sum())",
            "",
            "pass_fail_counts = {}",
            "pass_fail_rates = {}",
            "if pass_column:",
            "    counts = df[pass_column].value_counts(dropna=False).to_dict()",
            "    for raw_value, raw_count in counts.items():",
            "        label = _json_label(raw_value)",
            "        count = int(raw_count)",
            "        rate = float(count / total_count) if total_count else 0.0",
            "        pass_fail_counts[label] = count",
            "        pass_fail_rates[label] = rate",
            "        rows.append({'section': 'pass_fail', 'label': label, 'count': count, 'rate': rate})",
            "else:",
            "    warnings.append('PassOrFail column is not available')",
            "",
            "defect_reasons = {}",
            "for column in reason_columns:",
            "    label = column.removeprefix('Reason_')",
            "    count = _active_count(column)",
            "    defect_reasons[label] = count",
            "    rows.append({",
            "        'section': 'defect_reason',",
            "        'label': label,",
            "        'count': count,",
            "        'rate': float(count / total_count) if total_count else 0.0,",
            "    })",
            "",
            "product_source = 'PART_NO'",
            "product_columns = part_no_columns",
            "if not product_columns:",
            "    product_source = 'PART_NAME'",
            "    product_columns = part_name_columns",
            "product_production = {}",
            "for column in product_columns:",
            "    label = column.removeprefix(product_source + '_')",
            "    count = _active_count(column)",
            "    product_production[label] = count",
            "    rows.append({",
            "        'section': 'product_production',",
            "        'label': label,",
            "        'count': count,",
            "        'rate': float(count / total_count) if total_count else 0.0,",
            "    })",
            "if not product_columns:",
            "    warnings.append('product one-hot columns are not available')",
            "",
            "summary_parts = [f'총 {total_count}건을 기준으로 품질 현황을 집계했습니다.']",
            "if pass_fail_counts:",
            "    summary_parts.append('양품/불량 값 분포를 계산했습니다.')",
            "if defect_reasons:",
            "    summary_parts.append('불량 사유별 건수를 계산했습니다.')",
            "if product_production:",
            "    summary_parts.append(f'{product_source}별 생산량을 계산했습니다.')",
            "summary = ' '.join(summary_parts)",
            "raw_metrics = {",
            "    'total_count': total_count,",
            "    'pass_fail_counts': pass_fail_counts,",
            "    'pass_fail_rates': pass_fail_rates,",
            "    'defect_reasons': defect_reasons,",
            "    'product_production': product_production,",
            "    'logical_columns': {",
            "        'product_source': product_source if product_columns else None,",
            "        'product_columns': product_columns,",
            "        'reason_columns': reason_columns,",
            "    },",
            "    'warnings': warnings,",
            "}",
            "print(json.dumps({",
            "    'summary': summary,",
            "    'table': rows,",
            "    'raw_metrics': raw_metrics,",
            "    'used_columns': used_columns,",
            "}, ensure_ascii=False))",
        ]
    )


def build_logical_group_count_code(plan: AnalysisPlan) -> str | None:
    if len(plan.group_by) != 1 or len(plan.metrics) != 1:
        return None
    metric = plan.metrics[0]
    if metric.aggregation != "count" or metric.column is not None:
        return None
    group_column = plan.group_by[0]
    family_columns = _one_hot_columns(plan, group_column)
    if not family_columns:
        return None
    used_columns = _ordered_existing_columns(plan, family_columns)
    alias = metric.alias
    return "\n".join(
        [
            f"group_column = {group_column!r}",
            f"family_columns = {family_columns!r}",
            f"used_columns = {used_columns!r}",
            f"metric_alias = {alias!r}",
            "rows = []",
            "for column in family_columns:",
            "    values = pd.to_numeric(df[column], errors='coerce').fillna(0)",
            "    count = int((values > 0).sum())",
            "    label = column.removeprefix(group_column + '_')",
            "    rows.append({group_column: label, metric_alias: count})",
            "total_count = int(len(df))",
            "raw_metrics = {",
            "    'total_count': total_count,",
            "    'group_count': int(len(rows)),",
            "    'logical_column': group_column,",
            "    'source_columns': family_columns,",
            "}",
            "summary = f'총 {total_count}건을 기준으로 {group_column}별 건수를 계산했습니다.'",
            "print(json.dumps({",
            "    'summary': summary,",
            "    'table': rows,",
            "    'raw_metrics': raw_metrics,",
            "    'used_columns': used_columns,",
            "}, ensure_ascii=False))",
        ]
    )


def _is_quality_summary_plan(plan: AnalysisPlan) -> bool:
    analysis_type = plan.analysis_type.lower()
    if analysis_type == "quality_status_summary":
        return True
    text = f"{plan.analysis_type} {plan.objective}".lower()
    return any(term.lower() in text for term in _QUALITY_TERMS)


def _one_hot_columns(plan: AnalysisPlan, logical_name: str) -> list[str]:
    prefix = _ONE_HOT_PREFIXES.get(logical_name)
    if prefix is None:
        return []
    return [
        column
        for column in plan.metadata_snapshot.columns
        if column.startswith(prefix) and column in plan.required_columns
    ]


def _ordered_existing_columns(
    plan: AnalysisPlan,
    candidates: Sequence[str | None],
) -> list[str]:
    available = set(plan.metadata_snapshot.columns)
    columns: list[str] = []
    for column in [*plan.required_columns, *candidates]:
        if column and column in available and column not in columns:
            columns.append(column)
    return columns
