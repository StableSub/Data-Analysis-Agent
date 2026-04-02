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
                        fill_value = self._numeric_impute_value(out[column], method="mean", column=column)
                        out[column] = out[column].fillna(fill_value)
                    elif operation.method == "median":
                        fill_value = self._numeric_impute_value(out[column], method="median", column=column)
                        out[column] = out[column].fillna(fill_value)
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
                    series = self._numeric_series_or_raise(out[column], operation="scale", column=column)
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

            if operation.op == "encode_categorical":
                if not operation.columns:
                    raise ValueError("encode_categorical requires 'columns'")
                if operation.method not in {"one_hot", "label"}:
                    raise ValueError("encode_categorical.method must be one_hot or label")
                for column in operation.columns:
                    if column not in out.columns:
                        raise ValueError(f"Column not found: {column}")
                if operation.method == "one_hot":
                    out = pd.get_dummies(out, columns=operation.columns, prefix=operation.columns, dtype=int)
                else:
                    for column in operation.columns:
                        categories = sorted(out[column].dropna().unique().tolist(), key=str)
                        mapping = {category: index for index, category in enumerate(categories)}
                        out[column] = out[column].map(mapping)
                continue

            if operation.op == "parse_datetime":
                if not operation.columns:
                    raise ValueError("parse_datetime requires 'columns'")
                for column in operation.columns:
                    if column not in out.columns:
                        raise ValueError(f"Column not found: {column}")
                    out[column] = pd.to_datetime(
                        out[column],
                        format=operation.format,
                        errors="coerce",
                    )
                continue

            if operation.op == "outlier":
                if not operation.columns:
                    raise ValueError("outlier requires 'columns'")
                if operation.method not in {"zscore", "iqr"}:
                    raise ValueError("outlier.method must be zscore or iqr")
                if operation.strategy not in {"drop", "clip"}:
                    raise ValueError("outlier.strategy must be drop or clip")

                drop_mask = pd.Series([False] * len(out), index=out.index)
                for column in operation.columns:
                    if column not in out.columns:
                        raise ValueError(f"Column not found: {column}")

                    series = self._numeric_series_or_raise(out[column], operation="outlier", column=column)
                    if operation.method == "zscore":
                        mean = series.mean()
                        std = series.std(ddof=0)
                        if std == 0 or pd.isna(std):
                            continue
                        z_scores = (series - mean) / std
                        is_outlier = z_scores.abs() > operation.z_threshold
                        if operation.strategy == "drop":
                            drop_mask |= is_outlier
                        else:
                            lower = mean - operation.z_threshold * std
                            upper = mean + operation.z_threshold * std
                            out[column] = series.clip(lower=lower, upper=upper)
                    else:
                        q1 = series.quantile(0.25)
                        q3 = series.quantile(0.75)
                        iqr = q3 - q1
                        lower = q1 - operation.iqr_multiplier * iqr
                        upper = q3 + operation.iqr_multiplier * iqr
                        is_outlier = (series < lower) | (series > upper)
                        if operation.strategy == "drop":
                            drop_mask |= is_outlier
                        else:
                            out[column] = series.clip(lower=lower, upper=upper)

                if operation.strategy == "drop":
                    out = out[~drop_mask].reset_index(drop=True)
                continue

            raise ValueError(f"Unknown operation: {operation.op}")
        return out

    @staticmethod
    def _numeric_impute_value(series: pd.Series, *, method: str, column: str) -> float:
        numeric_series = PreprocessProcessor._numeric_series_or_raise(
            series,
            operation=f"impute.method '{method}'",
            column=column,
        )

        if method == "mean":
            value = numeric_series.mean()
        else:
            value = numeric_series.median()

        if pd.isna(value):
            raise ValueError(f"impute.method '{method}' requires a numeric column: {column}")
        return float(value)

    @staticmethod
    def _numeric_series_or_raise(series: pd.Series, *, operation: str, column: str) -> pd.Series:
        non_null = series.dropna()
        if non_null.empty:
            raise ValueError(f"{operation} requires a numeric column: {column}")

        numeric_series = pd.to_numeric(series, errors="coerce")
        numeric_ratio = float(numeric_series.dropna().shape[0]) / float(non_null.shape[0])
        if numeric_ratio < 0.98:
            raise ValueError(f"{operation} requires a numeric column: {column}")
        return numeric_series
