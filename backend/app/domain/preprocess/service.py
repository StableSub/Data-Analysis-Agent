import os
import re
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.domain.data_source.models import Dataset
from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.domain.preprocess.schemas import (
    PreprocessApplyResponse, 
    PreprocessOperation,
    DataSummary,
    NumericDistribution,
    SummaryDiff,
)

_SAFE_EXPR_RE = re.compile(r"^[0-9a-zA-Z_+\-*/%().\s<>=!&|]+$")

def _build_summary(df: pd.DataFrame) -> DataSummary:
    """데이터프레임의 요약 통계를 생성한다."""
    missing_by_column: dict[str, int] = {
        col: int(df[col].isna().sum()) for col in df.columns
    }
    numeric_distribution: dict[str, NumericDistribution] = {}
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        numeric_distribution[col] = NumericDistribution(
            min=float(s.min()) if len(s) else None,
            max=float(s.max()) if len(s) else None,
            mean=float(s.mean()) if len(s) else None,
            std=float(s.std(ddof=0)) if len(s) else None,
            p25=float(s.quantile(0.25)) if len(s) else None,
            p50=float(s.quantile(0.50)) if len(s) else None,
            p75=float(s.quantile(0.75)) if len(s) else None,
        )
    return DataSummary(
        row_count=len(df),
        column_count=len(df.columns),
        missing_total=int(df.isna().sum().sum()),
        missing_by_column=missing_by_column,
        numeric_distribution=numeric_distribution,
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
    )


def _build_diff(before: DataSummary, after: DataSummary) -> SummaryDiff:
    """전처리 전후 변화량을 계산한다."""
    all_cols = set(before.missing_by_column) | set(after.missing_by_column)
    missing_delta = {
        col: after.missing_by_column.get(col, 0) - before.missing_by_column.get(col, 0)
        for col in all_cols
    }
    dtype_changes: dict[str, dict[str, str]] = {}
    for col in all_cols:
        b_dtype = before.dtypes.get(col)
        a_dtype = after.dtypes.get(col)
        if b_dtype and a_dtype and b_dtype != a_dtype:
            dtype_changes[col] = {"before": b_dtype, "after": a_dtype}
        elif b_dtype and not a_dtype:
            dtype_changes[col] = {"before": b_dtype, "after": "(dropped)"}
        elif not b_dtype and a_dtype:
            dtype_changes[col] = {"before": "(new)", "after": a_dtype}

    return SummaryDiff(
        row_count_delta=after.row_count - before.row_count,
        column_count_delta=after.column_count - before.column_count,
        missing_total_delta=after.missing_total - before.missing_total,
        missing_by_column_delta=missing_delta,
        dtype_changes=dtype_changes,
    )


class PreprocessService:
    """데이터셋에 전처리 연산을 적용하는 최소 서비스."""

    def __init__(self, db: Session):
        self.repository = DataSourceRepository(db)

    def apply(
        self,
        source_id: str,
        operations: list[PreprocessOperation],
    ) -> PreprocessApplyResponse:
        """선택한 source_id 데이터셋 CSV 파일에 전처리를 적용해 새 데이터셋으로 저장한다."""
        input_dataset = self.repository.get_by_source_id(source_id)
        if not input_dataset:
            raise FileNotFoundError(f"Dataset not found: {source_id}")
        if not input_dataset.storage_path:
            raise FileNotFoundError("Dataset file path not found")

        file_path = self._resolve_dataset_file(source_id)
        df = pd.read_csv(file_path)

        summary_before = _build_summary(df)
        processed = self._apply_operations(df, operations)

        summary_after = _build_summary(processed)
        summary_diff = _build_diff(summary_before, summary_after)

        output_path, output_filename = self._build_output_path(file_path)
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

    def _resolve_dataset_file(self, source_id: str) -> str:
        """source_id로 파일 경로를 조회하고 존재 여부를 검증한다."""
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            raise FileNotFoundError(f"Dataset not found: {source_id}")
        if not dataset.storage_path:
            raise FileNotFoundError("Dataset file path not found")
        if not os.path.exists(dataset.storage_path):
            raise FileNotFoundError(f"Dataset file missing: {dataset.storage_path}")
        return dataset.storage_path

    def _build_output_path(self, source_path: str) -> tuple[Path, str]:
        """원본 경로 기준으로 새 전처리 결과 파일 경로/파일명을 생성한다."""
        source = Path(source_path)
        output_filename = f"{source.stem}_preprocessed_{uuid.uuid4().hex[:8]}.csv"
        return source.with_name(output_filename), output_filename

    def _apply_operations(self, df: pd.DataFrame, operations: list[PreprocessOperation]) -> pd.DataFrame:
        """지원하는 최소 연산만 순서대로 적용한다."""
        out = df.copy()
        for operation in operations:
            if operation.op == "drop_missing":
                columns = operation.columns
                how = operation.how
                if how not in {"any", "all"}:
                    raise ValueError("drop_missing.how must be any or all")
                out = out.dropna(subset=columns, how=how) if columns else out.dropna(how=how)
                continue

            if operation.op == "drop_columns":
                if not operation.columns:
                    raise ValueError("drop_columns requires columns")
                out = out.drop(columns=operation.columns, errors="ignore")
                continue

            if operation.op == "rename_columns":
                rename_from = operation.rename_from
                rename_to = operation.rename_to
                if len(rename_from) != len(rename_to):
                    raise ValueError("rename_columns requires same length for rename_from and rename_to")
                if not rename_from and not rename_to:
                    raise ValueError("rename_columns requires rename_from and rename_to")
                mapping = {
                    old_name: new_name
                    for old_name, new_name in zip(rename_from, rename_to)
                    if old_name and new_name
                }
                out = out.rename(columns=mapping)
                continue

            if operation.op == "impute":
                method = operation.method
                columns = operation.columns
                value = operation.value
                if not columns:
                    raise ValueError("impute requires 'columns'")
                if method not in {"mean", "median", "mode", "value"}:
                    raise ValueError("impute.method must be mean, median, mode, or value")

                for col in columns:
                    if col not in out.columns:
                        raise ValueError(f"Column not found: {col}")
                    if method == "mean":
                        out[col] = out[col].fillna(out[col].mean(numeric_only=True))
                    elif method == "median":
                        out[col] = out[col].fillna(out[col].median(numeric_only=True))
                    elif method == "mode":
                        mode_values = out[col].mode(dropna=True)
                        out[col] = out[col].fillna(mode_values.iloc[0] if len(mode_values) else value)
                    elif method == "value":
                        out[col] = out[col].fillna(value)
                    else:
                        raise ValueError("impute.method must be one of: mean, median, mode, value")
                continue

            if operation.op == "scale":
                method = operation.method
                columns = operation.columns
                if not columns:
                    raise ValueError("scale requires 'columns'")
                if method not in {"standardize", "normalize"}:
                    raise ValueError("scale.method must be standardize or normalize")

                for col in columns:
                    if col not in out.columns:
                        raise ValueError(f"Column not found: {col}")
                    series = pd.to_numeric(out[col], errors="coerce")
                    if method == "standardize":
                        mean = series.mean()
                        std = series.std(ddof=0)
                        out[col] = series if std == 0 or pd.isna(std) else (series - mean) / std
                    elif method == "normalize":
                        min_val = series.min()
                        max_val = series.max()
                        denom = max_val - min_val
                        out[col] = series if denom == 0 or pd.isna(denom) else (series - min_val) / denom
                    else:
                        raise ValueError("scale.method must be one of: standardize, normalize")
                continue

            if operation.op == "derived_column":
                new_col = operation.name
                expr = operation.expression
                if not new_col or not expr:
                    raise ValueError("derived_column requires 'name' and 'expression'")
                if not _SAFE_EXPR_RE.match(expr):
                    raise ValueError("derived_column.expression contains unsupported characters")
                out[new_col] = out.eval(expr, engine="python")
                continue
            
            if operation.op == "encode_categorical":
                columns = operation.columns
                method = operation.method
                if not columns:
                    raise ValueError("encode_categorical requires 'columns'")
                if method not in {"one_hot", "label"}:
                    raise ValueError("encode_categorical.method must be one_hot or label")

                for col in columns:
                    if col not in out.columns:
                        raise ValueError(f"Column not found: {col}")

                if method == "one_hot":
                    out = pd.get_dummies(out, columns=columns, prefix=columns, dtype=int)

                elif method == "label":
                    for col in columns:
                        # 재현성을 위해 정렬된 unique 값 기준으로 매핑
                        categories = sorted(out[col].dropna().unique().tolist(), key=str)
                        mapping = {cat: idx for idx, cat in enumerate(categories)}
                        out[col] = out[col].map(mapping)
                continue
            
            if operation.op == "parse_datetime":
                columns = operation.columns
                fmt = operation.format  # None 이면 pandas 자동 추론
                if not columns:
                    raise ValueError("parse_datetime requires 'columns'")

                for col in columns:
                    if col not in out.columns:
                        raise ValueError(f"Column not found: {col}")
                    out[col] = pd.to_datetime(out[col], format=fmt, errors="coerce")
                continue

            if operation.op == "outlier":
                columns = operation.columns
                method = operation.method
                strategy = operation.strategy
                if not columns:
                    raise ValueError("outlier requires 'columns'")
                if method not in {"zscore", "iqr"}:
                    raise ValueError("outlier.method must be zscore or iqr")
                if strategy not in {"drop", "clip"}:
                    raise ValueError("outlier.strategy must be drop or clip")

                drop_mask = pd.Series([False] * len(out), index=out.index)

                for col in columns:
                    if col not in out.columns:
                        raise ValueError(f"Column not found: {col}")
                    series = pd.to_numeric(out[col], errors="coerce")

                    if method == "zscore":
                        mean = series.mean()
                        std = series.std(ddof=0)
                        if std == 0 or pd.isna(std):
                            continue
                        z_scores = (series - mean) / std
                        is_outlier = z_scores.abs() > operation.z_threshold

                        if strategy == "drop":
                            drop_mask |= is_outlier
                        elif strategy == "clip":
                            lower = mean - operation.z_threshold * std
                            upper = mean + operation.z_threshold * std
                            out[col] = series.clip(lower=lower, upper=upper)

                    elif method == "iqr":
                        q1 = series.quantile(0.25)
                        q3 = series.quantile(0.75)
                        iqr = q3 - q1
                        lower = q1 - operation.iqr_multiplier * iqr
                        upper = q3 + operation.iqr_multiplier * iqr
                        is_outlier = (series < lower) | (series > upper)

                        if strategy == "drop":
                            drop_mask |= is_outlier
                        elif strategy == "clip":
                            out[col] = series.clip(lower=lower, upper=upper)

                if strategy == "drop":
                    out = out[~drop_mask].reset_index(drop=True)
                continue
            
            raise ValueError(f"Unknown operation: {operation.op}")

        return out
