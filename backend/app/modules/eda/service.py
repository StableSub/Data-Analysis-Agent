from pathlib import Path

import pandas as pd

from .schemas import (
    EDAColumnTypeItem,
    EDAColumnTypesResponse,
    EDACorrelationItem,
    EDACorrelationsResponse,
    EDADistributionBin,
    EDADistributionResponse,
    EDAPreprocessRecommendation,
    EDAPreprocessRecommendationsResponse,
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


class EDANotFoundError(LookupError):
    """Raised when a requested EDA resource does not exist."""


class EDAInvalidRequestError(ValueError):
    """Raised when the request shape is invalid for an EDA endpoint."""


class EDAUnsupportedRequestError(ValueError):
    """Raised when the request targets an unsupported EDA operation."""


def _safe_float(value: object, ndigits: int = 4) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), ndigits)


def _serialize_label_value(value: object) -> str:
    if pd.isna(value):
        return "null"
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    return str(value)


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
            return EDACorrelationsResponse(source_id=source_id, pairs=[])

        df = self.reader.read_csv(dataset.storage_path, usecols=numeric_columns)
        if df.empty:
            return EDACorrelationsResponse(source_id=source_id, pairs=[])

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

    def get_distribution(
        self,
        source_id: str,
        *,
        column: str,
        bins: int = 10,
        top_n: int = 10,
    ) -> EDADistributionResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None
        if column not in profile.columns:
            raise EDAInvalidRequestError(f"Unknown column: {column}")

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return None

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        inferred_type = profile.logical_types.get(column)
        if inferred_type is None:
            raise EDAInvalidRequestError(f"Unknown column type for: {column}")
        if inferred_type == "identifier":
            raise EDAUnsupportedRequestError("Identifier columns are not supported for distribution charts.")

        df = self.reader.read_csv(dataset.storage_path, usecols=[column])
        if df.empty:
            return EDADistributionResponse(
                source_id=source_id,
                column=column,
                inferred_type=inferred_type,
                chart_type="histogram" if inferred_type == "numerical" else "bar",
                total_count=0,
                bins=[],
            )

        series = df[column]
        if inferred_type == "numerical":
            numeric_series = pd.to_numeric(series, errors="coerce").dropna()
            if numeric_series.empty:
                return EDADistributionResponse(
                    source_id=source_id,
                    column=column,
                    inferred_type=inferred_type,
                    chart_type="histogram",
                    total_count=0,
                    bins=[],
                )

            if numeric_series.nunique() == 1:
                value = float(numeric_series.iloc[0])
                distribution_bins = [
                    EDADistributionBin(
                        label=str(_safe_float(value)),
                        value=int(len(numeric_series)),
                        lower=_safe_float(value),
                        upper=_safe_float(value),
                    )
                ]
            else:
                cut_result, edges = pd.cut(
                    numeric_series,
                    bins=max(1, bins),
                    include_lowest=True,
                    retbins=True,
                    duplicates="drop",
                )
                bin_counts = cut_result.value_counts(sort=False)
                distribution_bins = []
                for interval, count in bin_counts.items():
                    if pd.isna(interval):
                        continue
                    distribution_bins.append(
                        EDADistributionBin(
                            label=str(interval),
                            value=int(count),
                            lower=_safe_float(interval.left),
                            upper=_safe_float(interval.right),
                        )
                    )

            return EDADistributionResponse(
                source_id=source_id,
                column=column,
                inferred_type=inferred_type,
                chart_type="histogram",
                total_count=int(len(numeric_series)),
                bins=distribution_bins,
            )

        value_counts = (
            series.fillna("null")
            .map(_serialize_label_value)
            .value_counts(dropna=False)
            .head(max(1, top_n))
        )
        distribution_bins = [
            EDADistributionBin(label=str(label), value=int(count))
            for label, count in value_counts.items()
        ]
        return EDADistributionResponse(
            source_id=source_id,
            column=column,
            inferred_type=inferred_type,
            chart_type="bar",
            total_count=int(series.notna().sum()),
            bins=distribution_bins,
        )

    def get_preprocess_recommendations(
        self,
        source_id: str,
    ) -> EDAPreprocessRecommendationsResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        quality = self.get_quality(source_id)
        outliers = self.get_outliers(source_id)
        if quality is None or outliers is None:
            return None

        outlier_map = {item.column: item for item in outliers.columns}
        recommendations: list[EDAPreprocessRecommendation] = []
        dropped_columns: set[str] = set()

        for column in profile.identifier_columns:
            recommendations.append(
                EDAPreprocessRecommendation(
                    column=column,
                    recommendation_type="exclude_identifier",
                    priority="medium",
                    reason="거의 유일값으로 구성된 식별자 컬럼으로 분석 대상에서 제외하는 것이 좋습니다.",
                    suggested_operation={"op": "drop_columns", "columns": [column]},
                )
            )

        for column in profile.datetime_columns:
            recommendations.append(
                EDAPreprocessRecommendation(
                    column=column,
                    recommendation_type="parse_datetime",
                    priority="medium",
                    reason="날짜/시간 컬럼으로 분류되어 전처리 단계에서 datetime 파싱을 권장합니다.",
                    suggested_operation={"op": "parse_datetime", "columns": [column], "format": None},
                )
            )

        for column_profile in profile.column_profiles:
            column = column_profile.name
            null_ratio = column_profile.missing_rate
            inferred_type = column_profile.inferred_type

            if null_ratio >= 0.7:
                dropped_columns.add(column)
                recommendations.append(
                    EDAPreprocessRecommendation(
                        column=column,
                        recommendation_type="drop_column_candidate",
                        priority="high",
                        reason=f"결측 비율이 {null_ratio:.1%}로 매우 높아 컬럼 삭제를 우선 검토하는 것이 좋습니다.",
                        suggested_operation={"op": "drop_columns", "columns": [column]},
                    )
                )
                continue

            if null_ratio <= 0:
                continue

            if inferred_type == "numerical":
                recommendations.append(
                    EDAPreprocessRecommendation(
                        column=column,
                        recommendation_type="impute_missing",
                        priority="medium",
                        reason=f"수치형 컬럼이며 결측 비율이 {null_ratio:.1%}이므로 중앙값 대체를 추천합니다.",
                        suggested_operation={"op": "impute", "columns": [column], "method": "median"},
                    )
                )
            elif inferred_type in {"categorical", "boolean", "group_key"}:
                recommendations.append(
                    EDAPreprocessRecommendation(
                        column=column,
                        recommendation_type="impute_missing",
                        priority="medium",
                        reason=f"범주형 성격의 컬럼이며 결측 비율이 {null_ratio:.1%}이므로 최빈값 대체를 추천합니다.",
                        suggested_operation={"op": "impute", "columns": [column], "method": "mode"},
                    )
                )

        for column, outlier_info in outlier_map.items():
            if column in dropped_columns:
                continue
            if outlier_info.outlier_ratio < 0.05:
                continue
            recommendations.append(
                EDAPreprocessRecommendation(
                    column=column,
                    recommendation_type="handle_outliers",
                    priority="medium",
                    reason=(
                        f"IQR 기준 이상치 비율이 {outlier_info.outlier_ratio:.1%}로 높아 "
                        "클리핑 또는 제거를 검토하는 것이 좋습니다."
                    ),
                    suggested_operation={
                        "op": "outlier",
                        "columns": [column],
                        "method": "iqr",
                        "strategy": "clip",
                        "iqr_multiplier": 1.5,
                    },
                )
            )

        recommendations.sort(
            key=lambda item: (
                {"high": 0, "medium": 1, "low": 2}[item.priority],
                item.column,
                item.recommendation_type,
            )
        )
        return EDAPreprocessRecommendationsResponse(
            source_id=source_id,
            recommendation_count=len(recommendations),
            recommendations=recommendations,
        )
