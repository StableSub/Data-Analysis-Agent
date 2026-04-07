from pathlib import Path

import pandas as pd

from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader
from .schemas import ColumnProfile, ColumnProfileType, DatasetProfile

BOOLEAN_TOKENS = {
    "0",
    "1",
    "false",
    "true",
    "n",
    "no",
    "y",
    "yes",
    "f",
    "t",
}

IDENTIFIER_NAME_TOKENS = ("id", "uuid", "key", "code")
GROUP_KEY_NAME_TOKENS = (
    "store",
    "shop",
    "branch",
    "region",
    "country",
    "city",
    "state",
    "category",
    "segment",
    "group",
    "team",
    "department",
    "channel",
    "product",
    "brand",
    "cluster",
)


class DatasetProfileService:
    """Build reusable dataset profiles from uploaded CSV sources."""

    def __init__(
        self,
        *,
        repository: DataSourceRepository,
        reader: DatasetReader,
    ) -> None:
        self.repository = repository
        self.reader = reader

    def build_profile(self, source_id: str, *, sample_rows: int = 2000) -> DatasetProfile:
        if not source_id:
            return DatasetProfile(source_id="", available=False)

        dataset = self.repository.get_by_source_id(source_id)
        if not dataset or not dataset.storage_path:
            return DatasetProfile(source_id=source_id, available=False)

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return DatasetProfile(source_id=source_id, available=False)

        sample_df = self.reader.read_csv(dataset.storage_path, nrows=sample_rows)
        (
            total_row_count,
            full_missing_counts,
            missing_rates,
        ) = self._compute_missing_statistics(
            dataset.storage_path,
            columns=[str(column) for column in sample_df.columns.tolist()],
        )
        row_count = len(sample_df)

        numeric_columns: list[str] = []
        datetime_columns: list[str] = []
        categorical_columns: list[str] = []
        boolean_columns: list[str] = []
        identifier_columns: list[str] = []
        group_key_columns: list[str] = []
        column_profiles: list[ColumnProfile] = []
        for column in sample_df.columns:
            column_name = str(column)
            series = sample_df[column]
            non_null_series = series.dropna()
            inferred_type = self._infer_column_type(column_name=column_name, series=series, row_count=row_count)

            if inferred_type == "numerical":
                numeric_columns.append(column_name)
            elif inferred_type == "datetime":
                datetime_columns.append(column_name)
            elif inferred_type == "boolean":
                boolean_columns.append(column_name)
                categorical_columns.append(column_name)
            elif inferred_type == "identifier":
                identifier_columns.append(column_name)
            elif inferred_type == "group_key":
                group_key_columns.append(column_name)
                categorical_columns.append(column_name)
            else:
                categorical_columns.append(column_name)

            sample_values = [self._serialize_value(value) for value in non_null_series.head(3).tolist()]
            unique_count = int(non_null_series.nunique(dropna=True))
            column_profiles.append(
                ColumnProfile(
                    name=column_name,
                    raw_dtype=str(series.dtype),
                    inferred_type=inferred_type,
                    null_count=int(full_missing_counts.get(column_name, 0)),
                    missing_rate=float(missing_rates.get(column, 0.0)),
                    unique_count=unique_count,
                    unique_ratio=self._safe_ratio(unique_count, len(non_null_series)),
                    sample_values=sample_values,
                )
            )

        return DatasetProfile(
            source_id=source_id,
            available=True,
            row_count=total_row_count,
            sample_row_count=min(len(sample_df), 3),
            column_count=len(sample_df.columns),
            columns=[str(column) for column in sample_df.columns.tolist()],
            dtypes={str(column): str(dtype) for column, dtype in sample_df.dtypes.items()},
            missing_rates={str(column): float(rate) for column, rate in missing_rates.items()},
            sample_rows=self._build_sample_rows(sample_df),
            numeric_columns=numeric_columns,
            datetime_columns=datetime_columns,
            categorical_columns=categorical_columns,
            boolean_columns=boolean_columns,
            identifier_columns=identifier_columns,
            group_key_columns=group_key_columns,
            type_columns={
                "numerical": numeric_columns,
                "categorical": categorical_columns,
                "datetime": datetime_columns,
                "boolean": boolean_columns,
                "identifier": identifier_columns,
                "group_key": group_key_columns,
            },
            logical_types={
                profile.name: profile.inferred_type
                for profile in column_profiles
            },
            column_profiles=column_profiles,
        )

    @staticmethod
    def _compute_missing_statistics(
        storage_path: str,
        *,
        columns: list[str],
        chunksize: int = 10000,
    ) -> tuple[int, dict[str, int], dict[str, float]]:
        if not columns:
            return 0, {}, {}

        total_rows = 0
        missing_counts = {column: 0 for column in columns}
        for chunk in pd.read_csv(
            storage_path,
            encoding="utf-8",
            sep=",",
            chunksize=chunksize,
            usecols=columns,
        ):
            total_rows += len(chunk)
            null_counts = chunk.isna().sum()
            for column in columns:
                missing_counts[column] += int(null_counts.get(column, 0))

        missing_rates = {
            column: round(float(count) / float(total_rows), 3) if total_rows > 0 else 0.0
            for column, count in missing_counts.items()
        }
        return total_rows, missing_counts, missing_rates

    @staticmethod
    def _build_sample_rows(df: pd.DataFrame, *, limit: int = 3) -> list[dict[str, object]]:
        return [
            {
                str(column): DatasetProfileService._serialize_value(value)
                for column, value in row.items()
            }
            for row in df.head(limit).to_dict(orient="records")
        ]

    @staticmethod
    def _serialize_value(value: object) -> object:
        if pd.isna(value):
            return None
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        if hasattr(value, "item"):
            return value.item()
        return value

    def _infer_column_type(
        self,
        *,
        column_name: str,
        series: pd.Series,
        row_count: int,
    ) -> ColumnProfileType:
        if self._is_boolean_column(series):
            return "boolean"
        if self._is_datetime_column(series):
            return "datetime"
        if self._is_identifier_column(column_name=column_name, series=series, row_count=row_count):
            return "identifier"
        if self._is_numeric_column(series):
            return "numerical"
        if self._is_group_key_column(column_name=column_name, series=series, row_count=row_count):
            return "group_key"
        return "categorical"

    @staticmethod
    def _is_numeric_column(series: pd.Series) -> bool:
        if pd.api.types.is_bool_dtype(series):
            return False
        if pd.api.types.is_numeric_dtype(series):
            return True

        non_null = series.dropna()
        if non_null.empty:
            return False

        converted = pd.to_numeric(non_null, errors="coerce")
        return converted.notna().mean() >= 0.9

    @staticmethod
    def _is_datetime_column(series: pd.Series) -> bool:
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            return False

        non_null = series.dropna()
        if non_null.empty:
            return False

        sample = non_null.astype(str).head(100)
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        return parsed.notna().mean() >= 0.7

    @staticmethod
    def _is_boolean_column(series: pd.Series) -> bool:
        if pd.api.types.is_bool_dtype(series):
            return True

        non_null = series.dropna()
        if non_null.empty:
            return False

        normalized_values = {
            str(value).strip().lower()
            for value in non_null.tolist()
            if str(value).strip()
        }
        return 0 < len(normalized_values) <= 2 and normalized_values.issubset(BOOLEAN_TOKENS)

    @staticmethod
    def _is_identifier_column(
        *,
        column_name: str,
        series: pd.Series,
        row_count: int,
    ) -> bool:
        non_null = series.dropna()
        if non_null.empty or row_count == 0:
            return False

        unique_count = int(non_null.nunique(dropna=True))
        if unique_count <= 1:
            return False

        unique_ratio = DatasetProfileService._safe_ratio(unique_count, len(non_null))
        normalized_name = column_name.strip().lower()
        name_suggests_identifier = any(
            normalized_name == token
            or normalized_name.endswith(f"_{token}")
            or normalized_name.startswith(f"{token}_")
            for token in IDENTIFIER_NAME_TOKENS
        )
        is_numeric_like = DatasetProfileService._is_numeric_column(series)

        if name_suggests_identifier and unique_ratio >= 0.85:
            return True

        return (not is_numeric_like) and unique_ratio >= 0.98

    @staticmethod
    def _is_group_key_column(
        *,
        column_name: str,
        series: pd.Series,
        row_count: int,
    ) -> bool:
        non_null = series.dropna()
        if non_null.empty or row_count == 0:
            return False

        unique_count = int(non_null.nunique(dropna=True))
        unique_ratio = DatasetProfileService._safe_ratio(unique_count, len(non_null))
        normalized_name = column_name.strip().lower()
        name_suggests_group = any(token in normalized_name for token in GROUP_KEY_NAME_TOKENS)

        if unique_count <= 1:
            return False

        return name_suggests_group and 0.01 <= unique_ratio <= 0.5

    @staticmethod
    def _safe_ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(float(numerator) / float(denominator), 4)
