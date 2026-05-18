from __future__ import annotations

import csv
import math
from collections import Counter
from functools import lru_cache
from statistics import stdev
from typing import Any

from eval_cases import require_dataset_path

SCALED_COLUMNS = ["Injection_Time", "Filling_Time", "Plasticizing_Time", "Cycle_Time"]


@lru_cache(maxsize=None)
def header(dataset_name: str) -> tuple[str, ...]:
    path = require_dataset_path(dataset_name)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return tuple(next(csv.reader(handle)))


@lru_cache(maxsize=None)
def dataset_shape(dataset_name: str) -> dict[str, int]:
    path = require_dataset_path(dataset_name)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        row_count = sum(1 for _ in reader)
    return {"row_count": row_count, "column_count": len(columns)}


@lru_cache(maxsize=None)
def label_counts(dataset_name: str, column: str = "PassOrFail") -> dict[str, int]:
    if column not in header(dataset_name):
        return {}
    path = require_dataset_path(dataset_name)
    counts: Counter[str] = Counter()
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            counts[str(row.get(column, ""))] += 1
    return dict(counts)


@lru_cache(maxsize=None)
def numeric_mean_std(dataset_name: str, columns_key: tuple[str, ...]) -> dict[str, dict[str, float]]:
    columns = list(columns_key)
    missing = sorted(set(columns) - set(header(dataset_name)))
    if missing:
        raise AssertionError(f"{dataset_name} is missing numeric columns: {missing}")
    values: dict[str, list[float]] = {column: [] for column in columns}
    path = require_dataset_path(dataset_name)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            for column in columns:
                raw_value = row.get(column)
                if raw_value in (None, ""):
                    continue
                values[column].append(float(raw_value))
    return {
        column: {
            "mean": sum(column_values) / len(column_values),
            "std": stdev(column_values),
        }
        for column, column_values in values.items()
    }


def is_scaled_like(
    stats: dict[str, dict[str, float]],
    *,
    mean_abs_max: float = 0.05,
    std_min: float = 0.95,
    std_max: float = 1.05,
) -> bool:
    return all(
        math.isclose(values["mean"], 0.0, abs_tol=mean_abs_max)
        and std_min <= values["std"] <= std_max
        for values in stats.values()
    )
