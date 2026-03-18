from typing import Any, Dict, List

import pandas as pd


def build_report_payload(
    *,
    analysis_results: List[Dict[str, Any]],
    visualizations: List[Dict[str, Any]],
    insights: List[Any],
) -> Dict[str, Any]:
    return {
        "analysis_results": analysis_results,
        "visualizations": visualizations,
        "insights": insights,
    }


def _safe_float(value: Any, ndigits: int = 4) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), ndigits)


def build_dataset_metrics(*, df: pd.DataFrame, source_id: str) -> Dict[str, Any]:
    row_count = int(df.shape[0])
    column_count = int(df.shape[1])
    total_cells = row_count * column_count
    missing_cells = int(df.isna().sum().sum())
    missing_rate = (missing_cells / total_cells) if total_cells > 0 else 0.0

    missing_by_column = df.isna().mean().sort_values(ascending=False)
    top_missing_columns = [
        {
            "column": str(column),
            "missing_rate": round(float(rate), 4),
        }
        for column, rate in missing_by_column.head(5).items()
        if float(rate) > 0
    ]

    numeric_df = df.select_dtypes(include="number")
    numeric_stats: list[Dict[str, Any]] = []
    for column in numeric_df.columns[:8]:
        series = numeric_df[column].dropna()
        if series.empty:
            continue
        numeric_stats.append(
            {
                "column": str(column),
                "min": _safe_float(series.min()),
                "max": _safe_float(series.max()),
                "mean": _safe_float(series.mean()),
                "median": _safe_float(series.median()),
                "std": _safe_float(series.std()),
            }
        )

    correlation_pairs: list[Dict[str, Any]] = []
    if numeric_df.shape[1] >= 2:
        corr_matrix = numeric_df.corr(numeric_only=True)
        cols = list(corr_matrix.columns)
        for i, col1 in enumerate(cols):
            for col2 in cols[i + 1 :]:
                value = corr_matrix.loc[col1, col2]
                if pd.isna(value):
                    continue
                corr_value = float(value)
                correlation_pairs.append(
                    {
                        "column_1": str(col1),
                        "column_2": str(col2),
                        "correlation": round(corr_value, 4),
                        "abs_corr": abs(corr_value),
                    }
                )
    correlation_pairs.sort(key=lambda item: item["abs_corr"], reverse=True)
    top_correlations = [
        {
            "column_1": item["column_1"],
            "column_2": item["column_2"],
            "correlation": item["correlation"],
        }
        for item in correlation_pairs[:5]
    ]

    return {
        "source_id": source_id,
        "row_count": row_count,
        "column_count": column_count,
        "missing": {
            "missing_cells": missing_cells,
            "total_cells": total_cells,
            "missing_rate": round(missing_rate, 4),
            "top_missing_columns": top_missing_columns,
        },
        "numeric_stats": numeric_stats,
        "top_correlations": top_correlations,
    }
