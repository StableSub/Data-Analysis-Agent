from __future__ import annotations

from typing import Literal, assert_never

import pandas as pd


NumericImputeMethod = Literal["mean", "median"]


def numeric_impute_value(series: pd.Series, *, method: NumericImputeMethod, column: str) -> float:
    numeric_series = numeric_series_or_raise(
        series,
        operation=f"impute.method '{method}'",
        column=column,
    )

    match method:
        case "mean":
            value = numeric_series.mean()
        case "median":
            value = numeric_series.median()
        case unreachable:
            assert_never(unreachable)

    if pd.isna(value):
        raise ValueError(f"impute.method '{method}' requires a numeric column: {column}")
    return float(value)


def numeric_series_or_raise(series: pd.Series, *, operation: str, column: str) -> pd.Series:
    non_null = series.dropna()
    if non_null.empty:
        raise ValueError(f"{operation} requires a numeric column: {column}")

    numeric_series = pd.to_numeric(series, errors="coerce")
    numeric_ratio = float(numeric_series.dropna().shape[0]) / float(non_null.shape[0])
    if numeric_ratio < 0.98:
        raise ValueError(f"{operation} requires a numeric column: {column}")
    return numeric_series
