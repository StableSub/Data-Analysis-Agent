from pathlib import Path

import pandas as pd

from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader
from .schemas import ColumnProfile, DatasetProfile


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
        numeric_columns = [str(column) for column in sample_df.select_dtypes(include="number").columns]
        datetime_columns = [
            str(column)
            for column in sample_df.columns
            if (
                pd.to_datetime(sample_df[column], errors="coerce").notna().mean() >= 0.7
                and str(column) not in numeric_columns
            )
        ]
        categorical_columns = [
            str(column)
            for column in sample_df.columns
            if str(column) not in numeric_columns and str(column) not in datetime_columns
        ]
        missing_rates = sample_df.isna().mean().round(3).to_dict()

        column_profiles: list[ColumnProfile] = []
        for column in sample_df.columns:
            column_name = str(column)
            if column_name in numeric_columns:
                inferred_type = "numerical"
            elif column_name in datetime_columns:
                inferred_type = "datetime"
            else:
                inferred_type = "categorical"

            series = sample_df[column].dropna().head(3)
            sample_values = [self._serialize_value(value) for value in series.tolist()]
            column_profiles.append(
                ColumnProfile(
                    name=column_name,
                    raw_dtype=str(sample_df[column].dtype),
                    inferred_type=inferred_type,
                    missing_rate=float(missing_rates.get(column, 0.0)),
                    sample_values=sample_values,
                )
            )

        return DatasetProfile(
            source_id=source_id,
            available=True,
            row_count=len(sample_df),
            column_count=len(sample_df.columns),
            columns=[str(column) for column in sample_df.columns.tolist()],
            dtypes={str(column): str(dtype) for column, dtype in sample_df.dtypes.items()},
            missing_rates={str(column): float(rate) for column, rate in missing_rates.items()},
            sample_rows=self._build_sample_rows(sample_df),
            numeric_columns=numeric_columns,
            datetime_columns=datetime_columns,
            categorical_columns=categorical_columns,
            column_profiles=column_profiles,
        )

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
