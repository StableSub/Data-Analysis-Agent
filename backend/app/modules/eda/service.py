from .schemas import (
    EDAProfileResponse,
    EDAQualityColumn,
    EDAQualityResponse,
    EDASummaryCounts,
    EDASummaryResponse,
)
from ..profiling.service import DatasetProfileService


class EDAService:
    """EDA read APIs backed by the shared profiling service."""

    def __init__(self, *, profile_service: DatasetProfileService) -> None:
        self.profile_service = profile_service

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
