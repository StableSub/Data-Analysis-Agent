from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
from .ai import draft_report, generate_summary_from_payload
from .models import Report
from .repository import ReportRepository


def _build_report_payload(
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


def _build_dataset_metrics(*, df: pd.DataFrame, source_id: str) -> Dict[str, Any]:
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


class ReportService:
    """리포트 persistence와 direct 생성 흐름을 담당한다."""

    def __init__(
        self,
        repository: ReportRepository,
        *,
        dataset_repository: DatasetRepository | None = None,
        reader: DatasetReader | None = None,
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.repository = repository
        self.dataset_repository = dataset_repository
        self.reader = reader
        self.default_model = default_model

    async def create_report(self, *, session_id: int, summary_text: str) -> Report:
        return self.repository.create(
            Report(
                session_id=session_id,
                summary_text=summary_text,
            )
        )

    def get_report(self, report_id: str) -> Report:
        report = self.repository.get(report_id)
        if not report:
            raise LookupError("REPORT_NOT_FOUND")
        return report

    def list_reports(self, session_id: int) -> List[Report]:
        return self.repository.list_by_session(session_id)

    def build_metrics_for_source(self, source_id: str) -> Dict[str, Any]:
        empty_metrics: Dict[str, Any] = {
            "source_id": source_id,
            "row_count": 0,
            "column_count": 0,
            "missing": {
                "missing_cells": 0,
                "total_cells": 0,
                "missing_rate": 0.0,
                "top_missing_columns": [],
            },
            "numeric_stats": [],
            "top_correlations": [],
        }
        if not source_id or self.dataset_repository is None or self.reader is None:
            return empty_metrics

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return empty_metrics

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return empty_metrics

        df = self.reader.read_csv(dataset.storage_path, nrows=5000)
        if df.empty:
            return empty_metrics
        return _build_dataset_metrics(df=df, source_id=source_id)

    def build_report_draft(
        self,
        *,
        question: str,
        source_id: str,
        insight_summary: str,
        visualization_summary: str,
        revision_instruction: str,
        model_id: str | None,
        visualizations: List[Dict[str, object]] | None = None,
        default_model: str | None = None,
    ) -> Dict[str, object]:
        metrics = self.build_metrics_for_source(source_id)
        report_text = draft_report(
            question=question,
            metrics=metrics,
            insight_summary=insight_summary,
            visualization_summary=visualization_summary,
            revision_instruction=revision_instruction,
            model_id=model_id,
            default_model=default_model or self.default_model,
        )
        return {
            "summary": report_text,
            "metrics": metrics,
            "visualizations": list(visualizations or []),
        }

    async def generate_summary(
        self,
        *,
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        insights: List[Any],
    ) -> str:
        if not analysis_results and not visualizations and not insights:
            raise LookupError("NO_RESULTS")

        payload = _build_report_payload(
            analysis_results=analysis_results,
            visualizations=visualizations,
            insights=insights,
        )

        try:
            return generate_summary_from_payload(
                payload=payload,
                model_id=None,
                default_model=self.default_model,
            )
        except Exception as exc:
            raise RuntimeError("GENERATION_ERROR") from exc

    async def create_report_from_request(
        self,
        *,
        session_id: int,
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        insights: List[Any],
    ) -> Report:
        summary_text = await self.generate_summary(
            analysis_results=analysis_results,
            visualizations=visualizations,
            insights=insights,
        )
        return await self.create_report(
            session_id=session_id,
            summary_text=summary_text,
        )
