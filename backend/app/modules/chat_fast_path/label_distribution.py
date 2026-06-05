from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

import numpy as np
import pandas as pd


_DEFECT_ANALYSIS_MIN_DEFECT_ROWS = 100
_PASS_OR_FAIL_COLUMN_NAMES = {"passorfail", "pass_or_fail", "pass fail", "불량여부"}
_NORMAL_LABELS = {"0", "y", "yes", "true", "pass", "passed", "ok", "normal", "정상", "양품", "합격"}
_DEFECT_LABELS = {"1", "n", "no", "false", "fail", "failed", "ng", "defect", "불량", "불합격"}


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

    normal = _find_label_row(table, _NORMAL_LABELS)
    defect = _find_label_row(table, _DEFECT_LABELS)
    if normal is None and defect is None:
        return None

    normal_count = _row_count(normal) if normal is not None else 0
    defect_count = _row_count(defect) if defect is not None else 0
    if normal_count is None or defect_count is None:
        return None
    normal_ratio = _row_ratio(normal) if normal is not None else 0.0
    defect_ratio = _row_ratio(defect) if defect is not None else 0.0

    return {
        "column": column,
        "total": total,
        "normal_label": normal.get("value") if normal is not None else "0",
        "defect_label": defect.get("value") if defect is not None else "1",
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

    if defect_count == 0:
        interpretation_sentence = (
            "현재 데이터에서는 불량 사례가 발견되지 않았습니다. "
            "따라서 전체 불량률이 0.00%라는 점은 말할 수 있지만, "
            "불량 원인이나 불량 조건을 비교해 찾을 근거는 없습니다."
        )
        uncertainty_sentence = (
            "불량 원인이나 불량 조건은 불량 사례와 가이드라인 근거 정보가 부족하여 "
            "이 부분은 정확하지 않을 수 있습니다."
        )
    elif sufficiency_status == "limited_for_segments":
        interpretation_sentence = (
            f"불량 샘플이 {defect_count}건이라 전체 불량률 확인은 가능하지만, "
            "제품별/날짜별/원인별로 나누는 세부 분석에는 부족할 수 있습니다."
        )
        uncertainty_sentence = (
            "불량 원인이나 제품별/날짜별 차이는 추가 컬럼 분석 또는 가이드라인 근거 정보가 부족하여 "
            "이 부분은 정확하지 않을 수 있습니다."
        )
    else:
        interpretation_sentence = (
            f"불량 샘플이 {defect_count}건이라 전체 분포와 기본 그룹 비교는 가능하지만 "
            "세부 그룹으로 나눌수록 표본 수를 함께 확인해야 합니다."
        )
        uncertainty_sentence = (
            "구체적인 불량 원인은 라벨 분포만으로 단정할 수 없어, 원인 컬럼이나 가이드라인 근거가 "
            "부족하여 이 부분은 정확하지 않을 수 있습니다."
        )

    return (
        f"PassOrFail 라벨 분포입니다. 총 {total}건 중 정상 {normal_count}건"
        f"({normal_rate_pct:.2f}%), 불량 {defect_count}건({defect_rate_pct:.2f}%).\n\n"
        "현재 데이터로 정확히 답할 수 있는 부분: 전체 정상/불량 건수와 비율, "
        f"전체 불량률은 {defect_rate_pct:.2f}%입니다.\n"
        "부족하지 않은 부분: 이 수치는 선택된 데이터셋의 PassOrFail 컬럼에서 직접 계산했기 때문에 "
        "전체 라벨 분포를 이해하는 데 사용할 수 있습니다.\n"
        f"비전문가 관점(불량 분석): {interpretation_sentence}\n"
        f"주의: {uncertainty_sentence}"
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


def _find_label_row(
    table: Sequence[Mapping[str, Any]],
    labels: set[str],
) -> Mapping[str, Any] | None:
    for row in table:
        value = str(row.get("value", "")).strip().lower()
        if value in labels:
            return row
    return None


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
