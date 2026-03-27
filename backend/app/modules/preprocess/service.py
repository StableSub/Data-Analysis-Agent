import os
import uuid
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from ..datasets.models import Dataset
from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
from .processor import PreprocessProcessor
from .schemas import (
    DataSummary,
    NumericDistribution,
    PreprocessApplyResponse,
    PreprocessOperation,
    SummaryDiff,
)


def _safe_float(value: Any, ndigits: int = 4) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), ndigits)


def _build_summary(df: pd.DataFrame) -> DataSummary:
    missing_by_column = {column: int(df[column].isna().sum()) for column in df.columns}
    numeric_distribution: dict[str, NumericDistribution] = {}
    for column in df.select_dtypes(include="number").columns:
        series = df[column].dropna()
        numeric_distribution[str(column)] = NumericDistribution(
            min=_safe_float(series.min()) if len(series) else None,
            max=_safe_float(series.max()) if len(series) else None,
            mean=_safe_float(series.mean()) if len(series) else None,
            std=_safe_float(series.std(ddof=0)) if len(series) else None,
            p25=_safe_float(series.quantile(0.25)) if len(series) else None,
            p50=_safe_float(series.quantile(0.50)) if len(series) else None,
            p75=_safe_float(series.quantile(0.75)) if len(series) else None,
        )
    return DataSummary(
        row_count=len(df),
        column_count=len(df.columns),
        missing_total=int(df.isna().sum().sum()),
        missing_by_column=missing_by_column,
        numeric_distribution=numeric_distribution,
        dtypes={str(column): str(dtype) for column, dtype in df.dtypes.items()},
    )


def _build_diff(before: DataSummary, after: DataSummary) -> SummaryDiff:
    all_columns = set(before.missing_by_column) | set(after.missing_by_column)
    missing_delta = {
        column: after.missing_by_column.get(column, 0) - before.missing_by_column.get(column, 0)
        for column in all_columns
    }
    dtype_changes: dict[str, dict[str, str]] = {}
    for column in all_columns:
        before_dtype = before.dtypes.get(column)
        after_dtype = after.dtypes.get(column)
        if before_dtype and after_dtype and before_dtype != after_dtype:
            dtype_changes[column] = {"before": before_dtype, "after": after_dtype}
        elif before_dtype and not after_dtype:
            dtype_changes[column] = {"before": before_dtype, "after": "(dropped)"}
        elif not before_dtype and after_dtype:
            dtype_changes[column] = {"before": "(new)", "after": after_dtype}

    return SummaryDiff(
        row_count_delta=after.row_count - before.row_count,
        column_count_delta=after.column_count - before.column_count,
        missing_total_delta=after.missing_total - before.missing_total,
        missing_by_column_delta=missing_delta,
        dtype_changes=dtype_changes,
    )


class PreprocessService:
    """전처리 실행 흐름만 담당한다."""

    def __init__(
        self,
        *,
        repository: DatasetRepository,
        reader: DatasetReader,
        processor: PreprocessProcessor,
    ) -> None:
        self.repository = repository
        self.reader = reader
        self.processor = processor

    def build_dataset_profile(self, source_id: str) -> Dict[str, Any]:
        if not source_id:
            return {"available": False}

        dataset = self.repository.get_by_source_id(source_id)
        if not dataset or not dataset.storage_path:
            return {"available": False}

        file_path = Path(dataset.storage_path)
        if not file_path.exists():
            return {"available": False}

        sample_df = self.reader.read_csv(dataset.storage_path, nrows=2000)
        numeric_cols = sample_df.select_dtypes(include="number").columns.tolist()
        datetime_cols = [
            col
            for col in sample_df.columns
            if (
                pd.to_datetime(sample_df[col], errors="coerce").notna().mean() >= 0.7
                and col not in numeric_cols
            )
        ]
        categorical_cols = [
            col
            for col in sample_df.columns
            if col not in numeric_cols and col not in datetime_cols
        ]
        sample_rows = sample_df.head(3)
        return {
            "available": True,
            "sample_row_count": len(sample_df),
            "columns": sample_df.columns.tolist(),
            "dtypes": sample_df.dtypes.astype(str).to_dict(),
            "missing_rates": sample_df.isna().mean().round(3).to_dict(),
            "sample_values": sample_rows.where(
                sample_rows.notnull(),
                None,
            ).to_dict(orient="list"),
            "numeric_columns": [str(c) for c in numeric_cols],
            "datetime_columns": [str(c) for c in datetime_cols],
            "categorical_columns": [str(c) for c in categorical_cols],
        }

    def apply(
        self,
        source_id: str,
        operations: list[PreprocessOperation],
    ) -> PreprocessApplyResponse:
        input_dataset = self.repository.get_by_source_id(source_id)
        if not input_dataset:
            raise FileNotFoundError(f"Dataset not found: {source_id}")
        if not input_dataset.storage_path:
            raise FileNotFoundError("Dataset file path not found")

        df = self.reader.read_csv(input_dataset.storage_path)
        summary_before = _build_summary(df)
        processed = self.processor.apply_operations(df, operations)
        summary_after = _build_summary(processed)
        summary_diff = _build_diff(summary_before, summary_after)
        output_path, output_filename = self._build_output_path(input_dataset.storage_path)
        processed.to_csv(output_path, index=False)
        output_size = os.path.getsize(output_path)

        output_dataset = self.repository.create(
            Dataset(
                filename=output_filename,
                storage_path=str(output_path),
                filesize=output_size,
            )
        )
        return PreprocessApplyResponse(
            input_source_id=source_id,
            output_source_id=output_dataset.source_id,
            output_filename=output_filename,
            summary_before=summary_before,
            summary_after=summary_after,
            summary_diff=summary_diff,
        )

    @staticmethod
    def _build_output_path(source_path: str) -> tuple[Path, str]:
        source = Path(source_path)
        output_filename = f"{source.stem}_preprocessed_{uuid.uuid4().hex[:8]}.csv"
        return source.with_name(output_filename), output_filename
