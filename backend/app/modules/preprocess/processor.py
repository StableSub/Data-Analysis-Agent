import re

import pandas as pd

from .schemas import PreprocessOperation

_SAFE_EXPR_RE = re.compile(r"^[0-9a-zA-Z_+\-*/%().\s<>=!&|]+$")


class PreprocessProcessor:
    """전처리 계산 로직만 담당한다."""

    def apply_operations(
        self,
        df: pd.DataFrame,
        operations: list[PreprocessOperation],
    ) -> pd.DataFrame:
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
                if not operation.columns:
                    raise ValueError("impute requires 'columns'")
                if operation.method not in {"mean", "median", "mode", "value"}:
                    raise ValueError("impute.method must be mean, median, mode, or value")
                for column in operation.columns:
                    if column not in out.columns:
                        raise ValueError(f"Column not found: {column}")
                    if operation.method == "mean":
                        out[column] = out[column].fillna(out[column].mean(numeric_only=True))
                    elif operation.method == "median":
                        out[column] = out[column].fillna(out[column].median(numeric_only=True))
                    elif operation.method == "mode":
                        mode_values = out[column].mode(dropna=True)
                        out[column] = out[column].fillna(
                            mode_values.iloc[0] if len(mode_values) else operation.value
                        )
                    else:
                        out[column] = out[column].fillna(operation.value)
                continue

            if operation.op == "scale":
                if not operation.columns:
                    raise ValueError("scale requires 'columns'")
                if operation.method not in {"standardize", "normalize"}:
                    raise ValueError("scale.method must be standardize or normalize")
                for column in operation.columns:
                    if column not in out.columns:
                        raise ValueError(f"Column not found: {column}")
                    series = pd.to_numeric(out[column], errors="coerce")
                    if operation.method == "standardize":
                        mean = series.mean()
                        std = series.std(ddof=0)
                        out[column] = series if std == 0 or pd.isna(std) else (series - mean) / std
                    else:
                        min_val = series.min()
                        max_val = series.max()
                        denom = max_val - min_val
                        out[column] = (
                            series if denom == 0 or pd.isna(denom) else (series - min_val) / denom
                        )
                continue

            if operation.op == "derived_column":
                if not operation.name or not operation.expression:
                    raise ValueError("derived_column requires 'name' and 'expression'")
                if not _SAFE_EXPR_RE.match(operation.expression):
                    raise ValueError("derived_column.expression contains unsupported characters")
                out[operation.name] = out.eval(operation.expression, engine="python")
                continue

            raise ValueError(f"Unknown operation: {operation.op}")
        return out
