from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


_MAX_LISTED_COLUMNS = 20
_MAX_SAMPLE_ROWS = 3
_MAX_SAMPLE_COLUMNS = 8
_MAX_MISSING_COLUMNS = 10

_ANALYTIC_KEYWORDS = (
    "평균",
    "합계",
    "중앙값",
    "최대",
    "최소",
    "상관",
    "비율",
    "분포",
    "비교",
    "분석",
    "예측",
    "추천",
    "원인",
    "mean",
    "sum",
    "median",
    "max",
    "min",
    "correlation",
    "corr",
    "ratio",
    "distribution",
    "compare",
    "analysis",
)


@dataclass(frozen=True)
class FastDatasetAnswer:
    output: dict[str, Any]
    fast_path_result: dict[str, Any]


def try_fast_dataset_answer(
    question: str,
    dataset_context: Mapping[str, Any],
) -> FastDatasetAnswer | None:
    """Return a metadata-only answer for simple dataset lookup questions."""

    normalized_question = _normalize_question(question)
    if not normalized_question:
        return None
    if dataset_context.get("available") is not True:
        return None

    intent = _detect_dataset_lookup_intent(normalized_question)
    if intent is None:
        return None

    content = _build_answer_content(intent, dataset_context)
    if not content:
        return None

    return FastDatasetAnswer(
        output={
            "type": "fast_dataset_answer",
            "content": content,
        },
        fast_path_result={
            "status": "handled",
            "kind": "dataset_answer",
            "operation": intent,
            "eligibility_score": 1.0,
            "blockers": [],
        },
    )


def _normalize_question(question: str) -> str:
    return " ".join(str(question or "").strip().lower().split())


def _detect_dataset_lookup_intent(question: str) -> str | None:
    if any(keyword in question for keyword in _ANALYTIC_KEYWORDS):
        return None

    matched_intents = [
        intent
        for intent in ("summary", "missing", "sample_rows", "shape", "columns")
        if _matches_intent(question, intent)
    ]
    if len(matched_intents) != 1:
        return None
    return matched_intents[0]


def _matches_intent(question: str, intent: str) -> bool:
    if intent == "summary":
        return any(
            keyword in question
            for keyword in ("데이터셋 설명", "데이터 설명", "데이터셋 요약", "dataset summary", "describe dataset")
        )
    if intent == "missing":
        return any(keyword in question for keyword in ("결측", "missing", "null", "널", "빈값"))
    if intent == "sample_rows":
        return any(keyword in question for keyword in ("샘플", "예시", "미리보기", "sample", "preview"))
    if intent == "shape":
        has_row = any(keyword in question for keyword in ("행", "row", "rows"))
        has_column_count = any(keyword in question for keyword in ("열", "컬럼", "column", "columns"))
        return (
            (has_row and has_column_count)
            or "행열" in question
            or "행/열" in question
            or "shape" in question
            or "크기" in question
        )
    if intent == "columns":
        if any(keyword in question for keyword in ("행", "row", "rows", "개수", "count", "shape", "크기")):
            return False
        return any(keyword in question for keyword in ("컬럼", "열", "스키마", "변수", "column", "columns", "schema"))
    return False


def _build_answer_content(intent: str, dataset_context: Mapping[str, Any]) -> str:
    if intent == "summary":
        return _format_summary_answer(dataset_context)
    if intent == "missing":
        return _format_missing_answer(dataset_context)
    if intent == "sample_rows":
        return _format_sample_rows_answer(dataset_context)
    if intent == "shape":
        return _format_shape_answer(dataset_context)
    if intent == "columns":
        return _format_columns_answer(dataset_context)
    return ""


def _format_summary_answer(dataset_context: Mapping[str, Any]) -> str:
    filename = _as_text(dataset_context.get("filename")) or "선택된 데이터셋"
    row_count = _as_int(dataset_context.get("row_count_total"))
    column_count = _as_int(dataset_context.get("column_count"))
    columns = _as_text_list(dataset_context.get("columns"))
    missing_summary = _build_missing_summary(dataset_context)

    lines = [
        f"{filename} 데이터셋은 {row_count:,}행 {column_count:,}열로 구성되어 있습니다.",
        _format_column_preview(columns),
    ]
    if missing_summary:
        lines.append(missing_summary)
    return "\n".join(line for line in lines if line)


def _format_columns_answer(dataset_context: Mapping[str, Any]) -> str:
    columns = _as_text_list(dataset_context.get("columns"))
    if not columns:
        return "이 데이터셋에서 확인된 컬럼이 없습니다."

    dtypes = _as_mapping(dataset_context.get("dtypes"))
    column_items = []
    for column in columns[:_MAX_LISTED_COLUMNS]:
        dtype = _as_text(dtypes.get(column))
        column_items.append(f"{column} ({dtype})" if dtype else column)

    suffix = ""
    if len(columns) > _MAX_LISTED_COLUMNS:
        suffix = f"\n외 {len(columns) - _MAX_LISTED_COLUMNS:,}개 컬럼이 더 있습니다."
    return f"총 {len(columns):,}개 컬럼입니다.\n" + ", ".join(column_items) + suffix


def _format_sample_rows_answer(dataset_context: Mapping[str, Any]) -> str:
    sample_rows = _as_records(dataset_context.get("sample_rows"))
    if not sample_rows:
        return "표시할 샘플 행이 없습니다."

    columns = list(sample_rows[0].keys())[:_MAX_SAMPLE_COLUMNS]
    header = " | ".join(columns)
    separator = " | ".join("---" for _ in columns)
    rows = [
        " | ".join(_format_value(row.get(column)) for column in columns)
        for row in sample_rows[:_MAX_SAMPLE_ROWS]
    ]
    return "샘플 행입니다.\n\n" + "\n".join([header, separator, *rows])


def _format_shape_answer(dataset_context: Mapping[str, Any]) -> str:
    row_count = _as_int(dataset_context.get("row_count_total"))
    column_count = _as_int(dataset_context.get("column_count"))
    sample_count = _as_int(dataset_context.get("row_count_sample"))
    if sample_count and sample_count != row_count:
        return f"전체 데이터셋은 {row_count:,}행 {column_count:,}열입니다. 현재 프로파일 샘플은 {sample_count:,}행입니다."
    return f"전체 데이터셋은 {row_count:,}행 {column_count:,}열입니다."


def _format_missing_answer(dataset_context: Mapping[str, Any]) -> str:
    missing_summary = _build_missing_summary(dataset_context)
    if not missing_summary:
        return "결측치 요약 정보를 확인할 수 없습니다."
    return missing_summary


def _build_missing_summary(dataset_context: Mapping[str, Any]) -> str:
    quality_summary = _as_mapping(dataset_context.get("quality_summary"))
    missing_total = _as_int(quality_summary.get("missing_total"))
    missing_ratio = _as_float(quality_summary.get("missing_ratio"))
    top_missing_columns = _as_records(quality_summary.get("top_missing_columns"))

    if missing_total == 0:
        return "프로파일 기준 확인된 결측치는 없습니다."

    ratio_text = f"{missing_ratio:.2%}" if missing_ratio > 0 else "0.00%"
    lines = [f"프로파일 기준 결측치는 총 {missing_total:,}개이며, 전체 셀의 {ratio_text}입니다."]
    if top_missing_columns:
        items = []
        for item in top_missing_columns[:_MAX_MISSING_COLUMNS]:
            column = _as_text(item.get("column"))
            count = _as_int(item.get("missing_count"))
            rate = _as_float(item.get("missing_rate"))
            if column:
                items.append(f"{column}: {count:,}개 ({rate:.2%})")
        if items:
            lines.append("결측치가 많은 컬럼은 " + ", ".join(items) + "입니다.")
    return "\n".join(lines)


def _format_column_preview(columns: list[str]) -> str:
    if not columns:
        return ""
    preview = ", ".join(columns[:_MAX_LISTED_COLUMNS])
    if len(columns) > _MAX_LISTED_COLUMNS:
        preview = f"{preview} 외 {len(columns) - _MAX_LISTED_COLUMNS:,}개"
    return f"컬럼은 총 {len(columns):,}개이며, {preview} 등이 있습니다."


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _as_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if text.replace(".", "", 1).isdigit():
        return float(text)
    return 0.0


def _as_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _as_text(item))]


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_records(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _format_value(value: object) -> str:
    text = _as_text(value)
    if not text:
        return ""
    return text.replace("\n", " ")[:80]
