import os
import re
import uuid
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.domain.data_source.models import Dataset
from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.domain.preprocess.schemas import PreprocessApplyResponse, PreprocessOperation

_SAFE_EXPR_RE = re.compile(r"^[0-9a-zA-Z_+\-*/%().\s<>=!&|]+$")


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
        processed = self._apply_operations(df, operations)
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

            raise ValueError(f"Unknown operation: {operation.op}")

        return out
