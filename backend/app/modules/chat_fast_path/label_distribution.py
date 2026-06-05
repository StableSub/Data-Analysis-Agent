from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

import numpy as np
import pandas as pd


_DEFECT_ANALYSIS_MIN_DEFECT_ROWS = 100
_PASS_OR_FAIL_COLUMN_NAMES = {"passorfail", "pass_or_fail", "pass fail", "불량여부"}


def counts_table(
    counts: pd.Series,
    *,
    total: int,
    top_n: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value, count in counts.head(top_n).items():
        count_int = int(count)
        rows.append(
            {
                "value": serialize_value(value),
                "count": count_int,
                "ratio": round(float(count_int / total), 4) if total else 0.0,
            }
        )
    return rows


def pass_or_fail_metrics(
    *,
    column: str,
    table: Sequence[Mapping[str, Any]],
    total: int,
) -> dict[str, Any] | None:
    if not _is_pass_or_fail_column(column):
        return None

    by_value = {str(row.get("value", "")).strip(): row for row in table}
    normal = by_value.get("0")
    defect = by_value.get("1")
    if normal is None or defect is None:
        return None

    normal_count = _row_count(normal)
    defect_count = _row_count(defect)
    normal_ratio = _row_ratio(normal)
    defect_ratio = _row_ratio(defect)
    if normal_count is None or defect_count is None:
        return None

    return {
        "column": column,
        "total": total,
        "normal_count": normal_count,
        "defect_count": defect_count,
        "normal_rate_pct": round(normal_ratio * 100, 2),
        "defect_rate_pct": round(defect_ratio * 100, 2),
        "defect_analysis_sufficiency": _sufficiency_status(defect_count),
    }


def pass_or_fail_summary(metrics: Mapping[str, Any]) -> str:
    normal_count = int(metrics["normal_count"])
    defect_count = int(metrics["defect_count"])
    normal_rate_pct = float(metrics["normal_rate_pct"])
    defect_rate_pct = float(metrics["defect_rate_pct"])
    total = int(metrics["total"])
    sufficiency_status = str(metrics["defect_analysis_sufficiency"])

    if sufficiency_status == "limited_for_segments":
        sufficiency_sentence = (
            f"불량 샘플이 {defect_count}건뿐이라 전체 분포 확인은 가능하지만 "
            "제품별, 날짜별, 원인별 세부 분석에는 부족할 수 있습니다."
        )
    else:
        sufficiency_sentence = (
            f"불량 샘플이 {defect_count}건이라 기본 분포와 주요 그룹 비교는 가능하지만 "
            "세부 그룹으로 나눌수록 표본 수를 함께 확인해야 합니다."
        )

    return (
        f"PassOrFail 라벨 분포입니다. 총 {total}건 중 정상 {normal_count}건"
        f"({normal_rate_pct:.2f}%), 불량 {defect_count}건({defect_rate_pct:.2f}%). "
        f"불량 분석 관점에서는 {sufficiency_sentence}"
    )


def serialize_value(value: object) -> str:
    if value is None or value is pd.NaT:
        return "null"
    if isinstance(value, float) and math.isnan(value):
        return "null"
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    return str(value)


def _is_pass_or_fail_column(column: str) -> bool:
    normalized = column.strip().lower().replace("-", "_")
    compact = normalized.replace("_", "").replace(" ", "")
    return normalized in _PASS_OR_FAIL_COLUMN_NAMES or compact == "passorfail"


def _row_count(row: Mapping[str, Any]) -> int | None:
    count = row.get("count")
    return int(count) if isinstance(count, int | float) else None


def _row_ratio(row: Mapping[str, Any]) -> float:
    ratio = row.get("ratio")
    return float(ratio) if isinstance(ratio, int | float) else 0.0


def _sufficiency_status(defect_count: int) -> str:
    if defect_count < _DEFECT_ANALYSIS_MIN_DEFECT_ROWS:
        return "limited_for_segments"
    return "usable_with_segment_checks"
