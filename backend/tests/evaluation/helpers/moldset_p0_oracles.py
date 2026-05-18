from __future__ import annotations

import csv
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Any

from eval_cases import require_dataset_path

DATASET = "moldset_labeled.csv"
REQUIRED_COLUMNS = {
    "PassOrFail",
    "PART_NAME",
    "Reason",
    "TimeStamp",
    "PART_FACT_SERIAL",
    "PART_NO",
}


@lru_cache(maxsize=None)
def read_rows(dataset_name: str = DATASET) -> tuple[dict[str, str], ...]:
    path = require_dataset_path(dataset_name)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def header(dataset_name: str = DATASET) -> list[str]:
    path = require_dataset_path(dataset_name)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(next(csv.reader(handle)))


def expected_label_distribution() -> dict[str, float | int]:
    rows = read_rows()
    counts = Counter(row["PassOrFail"] for row in rows)
    defect_count = int(counts["1"])
    total_count = len(rows)
    return {
        "total_count": total_count,
        "normal_count": int(counts["0"]),
        "defect_count": defect_count,
        "defect_rate_pct": defect_count / total_count * 100,
    }


def expected_defect_rate_by_part() -> list[dict[str, Any]]:
    grouped: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in read_rows():
        part_name = row["PART_NAME"]
        grouped[part_name][0] += 1
        if row["PassOrFail"] == "1":
            grouped[part_name][1] += 1
    return [
        {
            "PART_NAME": part_name,
            "total_count": total_count,
            "defect_count": defect_count,
            "defect_rate_pct": defect_count / total_count * 100 if total_count else 0.0,
        }
        for part_name, (total_count, defect_count) in sorted(grouped.items())
    ]


def expected_defect_reason_counts() -> list[dict[str, Any]]:
    counts = Counter(
        row["Reason"].strip()
        for row in read_rows()
        if row["PassOrFail"] == "1" and row.get("Reason", "").strip()
    )
    return [
        {"Reason": reason, "defect_count": count}
        for reason, count in sorted(counts.items())
    ]
