from pathlib import Path

import pandas as pd
import logging

from .ai import generate_eda_ai_summary
from .schemas import (
    EDAAISummaryResponse,
    EDAColumnTypeItem,
    EDAColumnTypesResponse,
    EDACorrelationItem,
    EDACorrelationsResponse,
    EDADistributionBin,
    EDADistributionResponse,
    EDAOutlierColumn,
    EDAOutliersResponse,
    EDAProfileResponse,
    EDAQualityColumn,
    EDAQualityResponse,
    EDAStatsColumn,
    EDAStatsResponse,
    EDASummaryCounts,
    EDASummaryResponse,
    PreprocessRecommendation,
    PreprocessRecommendationResponse,
)
from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader
from ..profiling.schemas import DatasetProfile
from ..profiling.service import DatasetProfileService
from .ai import detect_issues, _issues_to_recommendation, recommend

logger = logging.getLogger(__name__)

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
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.profile_service = profile_service
        self.dataset_repository = dataset_repository
        self.reader = reader
        self.default_model = default_model

    def get_profile(self, source_id: str) -> EDAProfileResponse:
        profile = self.profile_service.build_profile(source_id)
        return EDAProfileResponse.model_validate(profile.model_dump())

    def get_summary(self, source_id: str) -> EDASummaryResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        return self._build_summary_response(profile)

    def get_quality(self, source_id: str) -> EDAQualityResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        return self._build_quality_response(profile)

    def get_column_types(self, source_id: str) -> EDAColumnTypesResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        return self._build_column_types_response(profile)

    def get_stats(self, source_id: str) -> EDAStatsResponse | None:
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        numeric_columns = [column for column in profile.numeric_columns if column]
        if not numeric_columns:
            return EDAStatsResponse(
                source_id=source_id,
                row_count=profile.row_count,
                column_count=profile.column_count,
                numeric_column_count=0,
                columns=[],
            )

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return None

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None

        df = self.reader.read_csv(dataset.storage_path, usecols=numeric_columns)
        if df.empty:
            return EDAStatsResponse(
                source_id=source_id,
                row_count=profile.row_count,
                column_count=profile.column_count,
                numeric_column_count=0,
                columns=[],
            )
        return self._build_stats_response(source_id, profile, df)

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

        return self._build_correlations_response(source_id, profile, df, limit=limit)

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

        return self._build_outliers_response(source_id, profile, df)

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
                    other_count=0,
                    truncated=False,
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
                total_count=sum(item.value for item in distribution_bins),
                other_count=0,
                truncated=False,
                bins=distribution_bins,
            )

        all_value_counts = (
            series.fillna("null")
            .map(_serialize_label_value)
            .value_counts(dropna=False)
        )
        value_counts = all_value_counts.head(max(1, top_n))
        distribution_bins = [
            EDADistributionBin(label=str(label), value=int(count))
            for label, count in value_counts.items()
        ]
        displayed_count = sum(item.value for item in distribution_bins)
        total_count = int(all_value_counts.sum())
        other_count = max(0, total_count - displayed_count)
        return EDADistributionResponse(
            source_id=source_id,
            column=column,
            inferred_type=inferred_type,
            chart_type="bar",
            total_count=total_count,
            other_count=other_count,
            truncated=other_count > 0,
            bins=distribution_bins,
        )

    
    def build_ai_summary_payload(self, source_id: str) -> dict[str, object] | None:
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
        summary = self._build_summary_response(profile)
        quality = self._build_quality_response(profile)
        column_types = self._build_column_types_response(profile)
        stats = self._build_stats_response(source_id, profile, df)
        correlations = self._build_correlations_response(source_id, profile, df, limit=3)
        outliers = self._build_outliers_response(source_id, profile, df)


        if (
            summary is None
            or quality is None
            or column_types is None
            or stats is None
            or correlations is None
            or outliers is None
        ):
            return None

        return {
            "source_id": source_id,
            "summary": summary.model_dump(),
            "quality": quality.model_dump(),
            "column_types": {
                "column_count": column_types.column_count,
                "type_columns": column_types.type_columns,
                "columns": [item.model_dump() for item in column_types.columns[:10]],
            },
            "stats": {
                "numeric_column_count": stats.numeric_column_count,
                "columns": [item.model_dump() for item in stats.columns[:10]],
            },
            "top_correlations": correlations.model_dump(),
            "outliers": {
                "numeric_column_count": outliers.numeric_column_count,
                "columns": [item.model_dump() for item in outliers.columns[:10]],
            },
        }

    def _build_summary_response(self, profile: DatasetProfile) -> EDASummaryResponse:
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

    def _build_quality_response(self, profile: DatasetProfile) -> EDAQualityResponse:
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

    def _build_column_types_response(self, profile: DatasetProfile) -> EDAColumnTypesResponse:
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

    def _build_stats_response(
        self,
        source_id: str,
        profile: DatasetProfile,
        df: pd.DataFrame,
    ) -> EDAStatsResponse:
        if df.empty:
            return EDAStatsResponse(
                source_id=source_id,
                row_count=0,
                column_count=0,
                numeric_column_count=0,
                columns=[],
            )

        numeric_columns = [column for column in profile.numeric_columns if column in df.columns]
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
                    skew=_safe_float(series.skew()) if len(series) else None,
                )
            )

        return EDAStatsResponse(
            source_id=source_id,
            row_count=profile.row_count,
            column_count=profile.column_count,
            numeric_column_count=len(stats_columns),
            columns=stats_columns,
        )

    def _build_correlations_response(
        self,
        source_id: str,
        profile: DatasetProfile,
        df: pd.DataFrame,
        *,
        limit: int,
    ) -> EDACorrelationsResponse:
        numeric_columns = [column for column in profile.numeric_columns if column in df.columns]
        if len(numeric_columns) < 2:
            return EDACorrelationsResponse(source_id=source_id, pairs=[])

        numeric_df = df[numeric_columns].apply(pd.to_numeric, errors="coerce")
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
        return EDACorrelationsResponse(
            source_id=source_id,
            pairs=[item for _, item in correlation_pairs[:limit]],
        )

    def _build_outliers_response(
        self,
        source_id: str,
        profile: DatasetProfile,
        df: pd.DataFrame,
    ) -> EDAOutliersResponse:
        numeric_columns = [column for column in profile.numeric_columns if column in df.columns]
        if not numeric_columns or df.empty:
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

        outlier_columns.sort(key=lambda item: (item.outlier_count, item.outlier_ratio), reverse=True)
        return EDAOutliersResponse(
            source_id=source_id,
            numeric_column_count=len(numeric_columns),
            columns=outlier_columns,
        )


    def get_ai_summary(
        self,
        source_id: str,
        *,
        model_id: str | None = None,
    ) -> EDAAISummaryResponse | None:
        payload = self.build_ai_summary_payload(source_id)
        if payload is None:
            return None

        summary_content = generate_eda_ai_summary(
            payload=payload,
            model_id=model_id,
            default_model=self.default_model,
        )
        return EDAAISummaryResponse(
            source_id=source_id,
            structure_summary=str(summary_content.get("structure_summary", "")).strip(),
            quality_issues=[str(item) for item in summary_content.get("quality_issues", [])],
            key_insights=[str(item) for item in summary_content.get("key_insights", [])],
        )

    def _build_prompt_summary(
        self,
        summary: EDASummaryResponse,
        quality: EDAQualityResponse,
        column_types: EDAColumnTypesResponse,
    ) -> dict:

        # 1. shape
        shape = {
            "rows": summary.row_count,
            "cols": summary.column_count,
        }

        # 2. missing (column: count)
        missing = {
            col.column: col.null_count
            for col in quality.columns
            if col.null_count > 0
        }

        # 3. dtypes (column: type)
        dtypes = {
            col.column: col.inferred_type
            for col in column_types.columns
        }

        return {
            "shape": shape,
            "missing": missing,
            "dtypes": dtypes,
        }
    
    def get_preprocess_recommendation(
        self,
        source_id: str,
        *,
        model_id: str | None = None,
    ) -> PreprocessRecommendation | None:
        """
        EDA 결과를 기반으로 전처리 추천 생성

        흐름:
        1. EDA 결과 생성
        2. rule-based로 detected_issues 생성
        3. LLM 입력용 summary 구성
        4. LLM 추천 시도
        5. 실패 시 fallback(rule-based) 반환
        """

        # 프로파일 로드
        profile = self.profile_service.build_profile(source_id)
        if not profile.available:
            return None

        # 기본 EDA 결과 생성
        summary = self._build_summary_response(profile)
        quality = self._build_quality_response(profile)
        column_types = self._build_column_types_response(profile)

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return None

        df = self.reader.read_csv(dataset.storage_path)

        stats = self._build_stats_response(source_id, profile, df)
        correlations = self._build_correlations_response(source_id, profile, df, limit=3)

        # 문제 감지 (rule-based)
        detected_issues = detect_issues(
            quality=quality,
            stats=stats,
            correlations=correlations,
            column_types=column_types,
        )


        # fallback 결과 
        fallback = _issues_to_recommendation(detected_issues)

        # LLM용 summary 구성 
        prompt_summary = self._build_prompt_summary(
            summary,
            quality,
            column_types,
        )

        # RAG — 아직 없으면 빈 문자열
        rag_context = ""

        # LLM 추천 시도
        try:
            result = recommend(
                eda_summary=prompt_summary,
                detected_issues=detected_issues,
                rag_context=rag_context,
                default_model=self.default_model,
                model_id=model_id,
            )

            return result

        except Exception as exc:
            logger.warning(
                "전처리 추천 LLM 실패 → fallback 사용. source_id=%s error=%s",
                source_id,
                exc,
            )
            return fallback