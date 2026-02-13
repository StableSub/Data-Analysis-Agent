import os
import re
from typing import List

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.domain.data_source.repository import DataSourceRepository
from backend.app.domain.preprocess.schemas import (
    ColumnPreview,
    PreprocessApplyResponse,
    PreprocessOperation,
    PreprocessPreviewResponse,
)

_SAFE_EXPR_RE = re.compile(r"^[0-9a-zA-Z_+\-*/%().\s<>=!&|]+$")


class PreprocessService:
    def __init__(self, db: Session):
        self.repository = DataSourceRepository(db)

    def preview(self, dataset_id: int) -> PreprocessPreviewResponse:
        file_path = self._resolve_dataset_file(dataset_id)
        df = self._read_dataframe(file_path)

        cols = [
            ColumnPreview(
                name=str(c),
                dtype=str(df[c].dtype),
                missing=int(df[c].isna().sum()),
            )
            for c in df.columns
        ]
        sample = df.head(20).where(pd.notnull(df), None).to_dict(orient="records")
        return PreprocessPreviewResponse(
            dataset_id=dataset_id,
            columns=cols,
            sample_rows=sample,
        )

    def apply(
        self,
        dataset_id: int,
        operations: List[PreprocessOperation],
    ) -> PreprocessApplyResponse:
        file_path = self._resolve_dataset_file(dataset_id)
        df = self._read_dataframe(file_path)
        df2 = self._apply_operations(df, operations)
        self._write_dataframe(df2, file_path)

        return PreprocessApplyResponse(
            dataset_id=dataset_id,
            row_count=int(df2.shape[0]),
            col_count=int(df2.shape[1]),
        )

    def _resolve_dataset_file(self, dataset_id: int) -> str:
        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            raise FileNotFoundError(f"Dataset not found: {dataset_id}")
        if not dataset.storage_path:
            raise FileNotFoundError("Dataset file path not found")
        if not os.path.exists(dataset.storage_path):
            raise FileNotFoundError(f"Dataset file missing: {dataset.storage_path}")
        return dataset.storage_path

    def _read_dataframe(self, file_path: str) -> pd.DataFrame:
        ext = os.path.splitext(file_path.lower())[1]
        if ext in [".csv", ".txt"]:
            return pd.read_csv(file_path)
        if ext in [".xlsx", ".xls"]:
            return pd.read_excel(file_path)
        if ext == ".parquet":
            return pd.read_parquet(file_path)
        raise ValueError(f"Unsupported file type: {ext}")

    def _write_dataframe(self, df: pd.DataFrame, out_path: str) -> None:
        ext = os.path.splitext(out_path.lower())[1]
        if ext == ".csv":
            df.to_csv(out_path, index=False)
            return
        if ext == ".parquet":
            df.to_parquet(out_path, index=False)
            return
        if ext in [".xlsx", ".xls"]:
            df.to_excel(out_path, index=False)
            return
        df.to_csv(out_path, index=False)

    def _apply_operations(self, df: pd.DataFrame, operations: List[PreprocessOperation]) -> pd.DataFrame:
        out = df.copy()

        for op in operations:
            name = op.op
            p = op.params or {}

            if name == "drop_missing":
                cols = p.get("columns") or []
                how = p.get("how", "any")
                out = out.dropna(subset=cols, how=how) if cols else out.dropna(how=how)

            elif name == "impute":
                method = p.get("method")
                cols = p.get("columns") or []
                value = p.get("value", None)

                if not cols:
                    raise ValueError("impute requires 'columns'")

                for c in cols:
                    if c not in out.columns:
                        raise ValueError(f"Column not found: {c}")

                    if method == "mean":
                        out[c] = out[c].fillna(out[c].mean(numeric_only=True))
                    elif method == "median":
                        out[c] = out[c].fillna(out[c].median(numeric_only=True))
                    elif method == "mode":
                        m = out[c].mode(dropna=True)
                        out[c] = out[c].fillna(m.iloc[0] if len(m) else value)
                    elif method == "value":
                        out[c] = out[c].fillna(value)
                    else:
                        raise ValueError("impute.method must be one of: mean, median, mode, value")

            elif name == "drop_columns":
                out = out.drop(columns=p.get("columns") or [], errors="ignore")

            elif name == "rename_columns":
                mapping = p.get("mapping") or {}
                if not isinstance(mapping, dict):
                    raise ValueError("rename_columns.mapping must be a dict")
                out = out.rename(columns=mapping)

            elif name == "scale":
                method = p.get("method")
                cols = p.get("columns") or []
                if not cols:
                    raise ValueError("scale requires 'columns'")

                for c in cols:
                    if c not in out.columns:
                        raise ValueError(f"Column not found: {c}")
                    s = pd.to_numeric(out[c], errors="coerce")
                    if method == "standardize":
                        mu = s.mean()
                        sd = s.std(ddof=0)
                        out[c] = s if sd == 0 or pd.isna(sd) else (s - mu) / sd
                    elif method == "normalize":
                        mn = s.min()
                        mx = s.max()
                        denom = mx - mn
                        out[c] = s if denom == 0 or pd.isna(denom) else (s - mn) / denom
                    else:
                        raise ValueError("scale.method must be one of: standardize, normalize")

            elif name == "derived_column":
                new_col = p.get("name")
                expr = p.get("expression")
                if not new_col or not expr:
                    raise ValueError("derived_column requires 'name' and 'expression'")
                if not _SAFE_EXPR_RE.match(expr):
                    raise ValueError("derived_column.expression contains unsupported characters")

                tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr))
                unknown = [t for t in tokens if t not in out.columns and t not in {"and", "or"}]
                if unknown:
                    raise ValueError(f"derived_column.expression references unknown columns: {unknown}")
                out[new_col] = out.eval(expr, engine="python")

            else:
                raise ValueError(f"Unknown operation: {name}")

        return out
