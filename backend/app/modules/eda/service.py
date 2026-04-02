from pathlib import Path

import pandas as pd

from .schemas import (
    EDAColumnTypeItem,
    EDAColumnTypesResponse,
    EDACorrelationItem,
    EDACorrelationsResponse,
    EDAOutlierColumn,
    EDAOutliersResponse,
    EDAProfileResponse,
    EDAQualityColumn,
    EDAQualityResponse,
    EDAStatsColumn,
    EDAStatsResponse,
    EDASummaryCounts,
    EDASummaryResponse,
)
from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader
from ..profiling.service import DatasetProfileService


def _safe_float(value: object, ndigits: int = 4) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), ndigits)


class EDAService:
    """EDA read APIs backed by the shared profiling service."""

    def __init__(
        self,
        *,
        profile_service: DatasetProfileService,
        dataset_repository: DataSourceRepository,
        reader: DatasetReader,
    ) -> None:
        self.profile_service = profile_service
        self.dataset_repository = dataset_repository
        self.reader = reader

    def get_profile(self, source_id: str) -> EDAProfileResponse:
        profile = self.profile_service.build_profile(source_id)
        return EDAProfileResponse.model_validate(profile.model_dump())

    def get_summary(self, source_id: str) -> EDASummaryResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        return EDASummaryResponse(
            source_id=profile.source_id,
            row_count=profile.row_count,
            column_count=profile.column_count,
            sample_row_count=profile.sample_row_count,
            type_counts=EDASummaryCounts(
                numerical=len(profile.numeric_columns),
                categorical=len(profile.categorical_columns),
                datetime=len(profile.datetime_columns),
                boolean=len(profile.boolean_columns),
                identifier=len(profile.identifier_columns),
                group_key=len(profile.group_key_columns),
            ),
            columns=profile.columns,
        )

    def get_quality(self, source_id: str) -> EDAQualityResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        quality_columns = [
            EDAQualityColumn(
                column=column_profile.name,
                inferred_type=column_profile.inferred_type,
                null_count=column_profile.null_count,
                null_ratio=column_profile.missing_rate,
            )
            for column_profile in profile.column_profiles
        ]
        quality_columns.sort(key=lambda item: (item.null_ratio, item.null_count), reverse=True)

        total_cells = profile.row_count * profile.column_count
        missing_total = sum(item.null_count for item in quality_columns)
        missing_ratio = round(float(missing_total) / float(total_cells), 4) if total_cells > 0 else 0.0

        return EDAQualityResponse(
            source_id=profile.source_id,
            row_count=profile.row_count,
            column_count=profile.column_count,
            missing_total=missing_total,
            missing_ratio=missing_ratio,
            top_missing_columns=[item for item in quality_columns if item.null_count > 0][:5],
            columns=quality_columns,
        )

    def get_column_types(self, source_id: str) -> EDAColumnTypesResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        return EDAColumnTypesResponse(
            source_id=profile.source_id,
            column_count=profile.column_count,
            type_columns=profile.type_columns,
            logical_types=profile.logical_types,
            columns=[
                EDAColumnTypeItem(
                    column=column_profile.name,
                    raw_dtype=column_profile.raw_dtype,
                    inferred_type=column_profile.inferred_type,
                    null_count=column_profile.null_count,
                    null_ratio=column_profile.missing_rate,
                    unique_count=column_profile.unique_count,
                    unique_ratio=column_profile.unique_ratio,
                    sample_values=column_profile.sample_values,
                )
                for column_profile in profile.column_profiles
            ],
        )

    def get_stats(self, source_id: str) -> EDAStatsResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return None

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        df = self.reader.read_csv(dataset.storage_path)
        if df.empty:
            return EDAStatsResponse(
                source_id=source_id,
                row_count=0,
                column_count=0,
                numeric_column_count=0,
                columns=[],
            )

        numeric_columns = [
            column
            for column in profile.numeric_columns
            if column in df.columns
        ]
        stats_columns: list[EDAStatsColumn] = []
        for column in numeric_columns:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            stats_columns.append(
                EDAStatsColumn(
                    column=column,
                    mean=_safe_float(series.mean()) if len(series) else None,
                    min=_safe_float(series.min()) if len(series) else None,
                    max=_safe_float(series.max()) if len(series) else None,
                    median=_safe_float(series.median()) if len(series) else None,
                    std=_safe_float(series.std(ddof=0)) if len(series) else None,
                    q1=_safe_float(series.quantile(0.25)) if len(series) else None,
                    q3=_safe_float(series.quantile(0.75)) if len(series) else None,
                )
            )

        return EDAStatsResponse(
            source_id=source_id,
            row_count=len(df),
            column_count=len(df.columns),
            numeric_column_count=len(stats_columns),
            columns=stats_columns,
        )

    def get_top_correlations(self, source_id: str, *, limit: int = 3) -> EDACorrelationsResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return None

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        numeric_columns = [column for column in profile.numeric_columns if column]
        if len(numeric_columns) < 2:
            return EDACorrelationsResponse(source_id=source_id, pair_count=0, pairs=[])

        df = self.reader.read_csv(dataset.storage_path, usecols=numeric_columns)
        if df.empty:
            return EDACorrelationsResponse(source_id=source_id, pair_count=0, pairs=[])

        numeric_df = df.apply(pd.to_numeric, errors="coerce")
        corr_matrix = numeric_df.corr(method="pearson", numeric_only=True)
        correlation_pairs: list[tuple[float, EDACorrelationItem]] = []
        columns = list(corr_matrix.columns)
        for index, column_1 in enumerate(columns):
            for column_2 in columns[index + 1 :]:
                value = corr_matrix.loc[column_1, column_2]
                if pd.isna(value):
                    continue
                corr_value = round(float(value), 4)
                correlation_pairs.append(
                    (
                        abs(corr_value),
                        EDACorrelationItem(
                            column_1=str(column_1),
                            column_2=str(column_2),
                            correlation=corr_value,
                        ),
                    )
                )

        correlation_pairs.sort(key=lambda item: item[0], reverse=True)
        pairs = [item for _, item in correlation_pairs[:limit]]
        return EDACorrelationsResponse(
            source_id=source_id,
            pair_count=len(pairs),
            pairs=pairs,
        )

    def get_outliers(self, source_id: str) -> EDAOutliersResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return None

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        numeric_columns = [column for column in profile.numeric_columns if column]
        if not numeric_columns:
            return EDAOutliersResponse(source_id=source_id, numeric_column_count=0, columns=[])

        df = self.reader.read_csv(dataset.storage_path, usecols=numeric_columns)
        if df.empty:
            return EDAOutliersResponse(source_id=source_id, numeric_column_count=0, columns=[])

        outlier_columns: list[EDAOutlierColumn] = []
        for column in numeric_columns:
            series = pd.to_numeric(df[column], errors="coerce").dropna()
            if series.empty:
                outlier_columns.append(EDAOutlierColumn(column=column))
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outlier_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = int(outlier_mask.sum())
            outlier_ratio = round(float(outlier_count) / float(len(series)), 4) if len(series) else 0.0
            outlier_columns.append(
                EDAOutlierColumn(
                    column=column,
                    outlier_count=outlier_count,
                    outlier_ratio=outlier_ratio,
                    q1=_safe_float(q1),
                    q3=_safe_float(q3),
                    iqr=_safe_float(iqr),
                    lower_bound=_safe_float(lower_bound),
                    upper_bound=_safe_float(upper_bound),
                )
            )

        outlier_columns.sort(
            key=lambda item: (item.outlier_count, item.outlier_ratio),
            reverse=True,
        )
        return EDAOutliersResponse(
            source_id=source_id,
            numeric_column_count=len(numeric_columns),
            columns=outlier_columns,
        )
