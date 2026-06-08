from __future__ import annotations

from collections.abc import Mapping

from .dataset_answer_values import (
    as_float,
    as_int,
    as_mapping,
    as_records,
    as_text,
    as_text_list,
    format_value,
)

_MAX_LISTED_COLUMNS = 20
_MAX_MAJOR_COLUMNS = 8
_MAX_SAMPLE_ROWS = 3
_MAX_SAMPLE_COLUMNS = 8
_MAX_MISSING_COLUMNS = 10


def build_answer_content(intent: str, dataset_context: Mapping[str, object]) -> str:
    if intent in {"summary", "shape", "row_count", "column_count"}:
        return _format_overview_answer(dataset_context)
    if intent == "missing":
        return _format_missing_answer(dataset_context)
    if intent == "sample_rows":
        return _format_sample_rows_answer(dataset_context)
    if intent in {
        "numeric_columns",
        "categorical_columns",
        "datetime_columns",
        "boolean_columns",
        "identifier_columns",
    }:
        return _format_typed_columns_answer(intent, dataset_context)
    if intent == "column_types":
        return _format_column_types_answer(dataset_context)
    if intent == "columns":
        return _format_columns_answer(dataset_context)
    return ""


def _format_overview_answer(dataset_context: Mapping[str, object]) -> str:
    filename = as_text(dataset_context.get("filename")) or "선택된 데이터셋"
    row_count = as_int(dataset_context.get("row_count_total"))
    column_count = as_int(dataset_context.get("column_count"))
    columns = as_text_list(dataset_context.get("columns"))
    lines = [f"데이터 크기: {filename} 데이터셋은 총 {row_count:,}행, {column_count:,}열입니다."]

    lines.append(_build_major_columns_section(dataset_context, columns))
    type_summary = _build_type_summary(dataset_context)
    if type_summary:
        lines.append(type_summary)
    missing_summary = _build_missing_summary(dataset_context)
    if missing_summary:
        lines.append(missing_summary)
    return "\n".join(line for line in lines if line)


def _build_major_columns_section(
    dataset_context: Mapping[str, object],
    columns: list[str],
) -> str:
    if not columns:
        return "주요 컬럼: 주요 컬럼 정보를 확인할 수 없습니다."

    roles_by_column = _build_column_roles(dataset_context)
    selected = _select_major_columns(columns, roles_by_column)
    items = [
        f"- {column}: {roles_by_column.get(column, '기타 컬럼')}"
        for column in selected
    ]
    remaining_count = max(len(columns) - len(selected), 0)
    if remaining_count > 0:
        items.append(f"- 그 외 {remaining_count:,}개 컬럼이 더 있습니다.")
    return "주요 컬럼:\n" + "\n".join(items)


def _build_column_roles(dataset_context: Mapping[str, object]) -> dict[str, str]:
    ordered_specs = (
        ("group_key_columns", "그룹/기준 컬럼"),
        ("datetime_columns", "날짜/시간형 컬럼"),
        ("numeric_columns", "숫자형 컬럼"),
        ("categorical_columns", "범주형 컬럼"),
        ("boolean_columns", "불리언 컬럼"),
        ("identifier_columns", "식별자 컬럼"),
    )
    roles: dict[str, str] = {}
    for key, label in ordered_specs:
        for column in as_text_list(dataset_context.get(key)):
            if column not in roles:
                roles[column] = label
    return roles


def _select_major_columns(
    columns: list[str],
    roles_by_column: Mapping[str, str],
) -> list[str]:
    selected: list[str] = []
    role_order = (
        "그룹/기준 컬럼",
        "날짜/시간형 컬럼",
        "숫자형 컬럼",
        "범주형 컬럼",
        "불리언 컬럼",
        "식별자 컬럼",
    )
    for role in role_order:
        for column in columns:
            if roles_by_column.get(column) == role and column not in selected:
                selected.append(column)
                if len(selected) == _MAX_MAJOR_COLUMNS:
                    return selected
    for column in columns:
        if column not in selected:
            selected.append(column)
            if len(selected) == _MAX_MAJOR_COLUMNS:
                return selected
    return selected


def _build_type_summary(dataset_context: Mapping[str, object]) -> str:
    type_specs = (
        ("숫자형", "numeric_columns"),
        ("날짜/시간형", "datetime_columns"),
        ("범주형", "categorical_columns"),
        ("불리언", "boolean_columns"),
        ("식별자", "identifier_columns"),
        ("그룹/기준", "group_key_columns"),
    )
    parts: list[str] = []
    for label, key in type_specs:
        count = len(as_text_list(dataset_context.get(key)))
        if count > 0:
            parts.append(f"{label} {count:,}개")
    if not parts:
        return ""
    return "컬럼 구성: " + ", ".join(parts) + "입니다."


def _format_columns_answer(dataset_context: Mapping[str, object]) -> str:
    columns = as_text_list(dataset_context.get("columns"))
    if not columns:
        return "이 데이터셋에서 확인된 컬럼이 없습니다."

    dtypes = as_mapping(dataset_context.get("dtypes"))
    column_items: list[str] = []
    for column in columns[:_MAX_LISTED_COLUMNS]:
        dtype = as_text(dtypes.get(column))
        column_items.append(f"{column} ({dtype})" if dtype else column)

    suffix = ""
    if len(columns) > _MAX_LISTED_COLUMNS:
        suffix = f"\n외 {len(columns) - _MAX_LISTED_COLUMNS:,}개 컬럼이 더 있습니다."
    return f"총 {len(columns):,}개 컬럼입니다.\n" + ", ".join(column_items) + suffix


def _format_column_types_answer(dataset_context: Mapping[str, object]) -> str:
    columns = as_text_list(dataset_context.get("columns"))
    dtypes = as_mapping(dataset_context.get("dtypes"))
    if not columns or not dtypes:
        return "데이터 타입 정보를 확인할 수 없습니다."

    type_items: list[str] = []
    for column in columns[:_MAX_LISTED_COLUMNS]:
        dtype = as_text(dtypes.get(column)) or "unknown"
        type_items.append(f"{column}: {dtype}")

    suffix = ""
    if len(columns) > _MAX_LISTED_COLUMNS:
        suffix = f"\n외 {len(columns) - _MAX_LISTED_COLUMNS:,}개 컬럼의 타입이 더 있습니다."
    return f"총 {len(columns):,}개 컬럼의 데이터 타입입니다.\n" + ", ".join(type_items) + suffix


def _format_typed_columns_answer(
    intent: str,
    dataset_context: Mapping[str, object],
) -> str:
    type_specs = {
        "numeric_columns": ("숫자형", "numeric_columns"),
        "categorical_columns": ("범주형", "categorical_columns"),
        "datetime_columns": ("날짜/시간형", "datetime_columns"),
        "boolean_columns": ("불리언", "boolean_columns"),
        "identifier_columns": ("식별자", "identifier_columns"),
    }
    label, context_key = type_specs[intent]
    columns = as_text_list(dataset_context.get(context_key))
    if not columns:
        return f"확인된 {label} 컬럼이 없습니다."

    dtypes = as_mapping(dataset_context.get("dtypes"))
    column_items: list[str] = []
    for column in columns[:_MAX_LISTED_COLUMNS]:
        dtype = as_text(dtypes.get(column))
        column_items.append(f"{column} ({dtype})" if dtype else column)

    suffix = ""
    if len(columns) > _MAX_LISTED_COLUMNS:
        suffix = f"\n외 {len(columns) - _MAX_LISTED_COLUMNS:,}개 {label} 컬럼이 더 있습니다."
    return f"총 {len(columns):,}개 {label} 컬럼입니다.\n" + ", ".join(column_items) + suffix


def _format_sample_rows_answer(dataset_context: Mapping[str, object]) -> str:
    sample_rows = as_records(dataset_context.get("sample_rows"))
    if not sample_rows:
        return "표시할 샘플 행이 없습니다."

    columns = list(sample_rows[0].keys())[:_MAX_SAMPLE_COLUMNS]
    header = " | ".join(columns)
    separator = " | ".join("---" for _ in columns)
    rows: list[str] = [
        " | ".join(format_value(row.get(column)) for column in columns)
        for row in sample_rows[:_MAX_SAMPLE_ROWS]
    ]
    return "샘플 행입니다.\n\n" + "\n".join([header, separator, *rows])


def _format_missing_answer(dataset_context: Mapping[str, object]) -> str:
    missing_summary = _build_missing_summary(dataset_context)
    if not missing_summary:
        return "결측치 요약 정보를 확인할 수 없습니다."
    return missing_summary


def _build_missing_summary(dataset_context: Mapping[str, object]) -> str:
    quality_summary = as_mapping(dataset_context.get("quality_summary"))
    if not quality_summary:
        return ""

    missing_total = as_int(quality_summary.get("missing_total"))
    missing_ratio = as_float(quality_summary.get("missing_ratio"))
    top_missing_columns = as_records(quality_summary.get("top_missing_columns"))

    if missing_total == 0:
        return "프로파일 기준 확인된 결측치는 없습니다."

    ratio_text = f"{missing_ratio:.2%}" if missing_ratio > 0 else "0.00%"
    lines: list[str] = [f"프로파일 기준 결측치는 총 {missing_total:,}개이며, 전체 셀의 {ratio_text}입니다."]
    if top_missing_columns:
        items: list[str] = []
        for item in top_missing_columns[:_MAX_MISSING_COLUMNS]:
            column = as_text(item.get("column"))
            count = as_int(item.get("missing_count"))
            rate = as_float(item.get("missing_rate"))
            if column:
                items.append(f"{column}: {count:,}개 ({rate:.2%})")
        if items:
            lines.append("결측치가 많은 컬럼은 " + ", ".join(items) + "입니다.")
    return "\n".join(lines)
