from __future__ import annotations

import math

import numpy as np
import pandas as pd


def finite_float(value: object, ndigits: int = 4) -> float | None:
    if value is None or pd.isna(value):
        return None

    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        return None

    return round(numeric_value, ndigits)


def finite_numeric_series(series: pd.Series) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce").astype("float64")
    return numeric_series[np.isfinite(numeric_series)]


def finite_numeric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    numeric_frame = frame.apply(pd.to_numeric, errors="coerce").astype("float64")
    return numeric_frame.where(np.isfinite(numeric_frame))
