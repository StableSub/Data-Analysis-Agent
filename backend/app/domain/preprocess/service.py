import os
import re
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.domain.preprocess.schemas import PreprocessApplyResponse, PreprocessOperation

_SAFE_EXPR_RE = re.compile(r"^[0-9a-zA-Z_+\-*/%().\s<>=!&|]+$")


class PreprocessService:
    """데이터셋에 전처리 연산을 적용하는 최소 서비스."""

    def __init__(self, db: Session):
        self.repository = DataSourceRepository(db)

    def apply(
        self,
        dataset_id: int,
        operations: List[PreprocessOperation],
    ) -> PreprocessApplyResponse:
        """선택한 데이터셋 CSV 파일에 전처리를 적용하고 같은 파일에 덮어쓴다."""
        file_path = self._resolve_dataset_file(dataset_id)
        df = pd.read_csv(file_path)
        processed = self._apply_operations(df, operations)
        processed.to_csv(file_path, index=False)
        return PreprocessApplyResponse(dataset_id=dataset_id)

    def _resolve_dataset_file(self, dataset_id: int) -> str:
        """dataset_id로 파일 경로를 조회하고 존재 여부를 검증한다."""
        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            raise FileNotFoundError(f"Dataset not found: {dataset_id}")
        if not dataset.storage_path:
            raise FileNotFoundError("Dataset file path not found")
        if not os.path.exists(dataset.storage_path):
            raise FileNotFoundError(f"Dataset file missing: {dataset.storage_path}")
        return dataset.storage_path

    def _apply_operations(self, df: pd.DataFrame, operations: List[PreprocessOperation]) -> pd.DataFrame:
        """지원하는 최소 연산만 순서대로 적용한다."""
        out = df.copy()
        for operation in operations:
            params: Dict[str, Any] = operation.params or {}

            if operation.op == "drop_missing":
                columns = params.get("columns") or []
                how = params.get("how", "any")
                out = out.dropna(subset=columns, how=how) if columns else out.dropna(how=how)
                continue

            if operation.op == "drop_columns":
                out = out.drop(columns=params.get("columns") or [], errors="ignore")
                continue

            if operation.op == "rename_columns":
                mapping = params.get("mapping") or {}
                if not isinstance(mapping, dict):
                    raise ValueError("rename_columns.mapping must be a dict")
                out = out.rename(columns=mapping)
                continue

            if operation.op == "impute":
                method = params.get("method")
                columns = params.get("columns") or []
                value = params.get("value", None)
                if not columns:
                    raise ValueError("impute requires 'columns'")

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
                method = params.get("method")
                columns = params.get("columns") or []
                if not columns:
                    raise ValueError("scale requires 'columns'")

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
                new_col = params.get("name")
                expr = params.get("expression")
                if not new_col or not expr:
                    raise ValueError("derived_column requires 'name' and 'expression'")
                if not _SAFE_EXPR_RE.match(expr):
                    raise ValueError("derived_column.expression contains unsupported characters")

                tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr))
                unknown = [token for token in tokens if token not in out.columns and token not in {"and", "or"}]
                if unknown:
                    raise ValueError(f"derived_column.expression references unknown columns: {unknown}")
                out[new_col] = out.eval(expr, engine="python")
                continue

            raise ValueError(f"Unknown operation: {operation.op}")

        return out
