from .schemas import EDAProfileResponse
from ..profiling.service import DatasetProfileService


class EDAService:
    """EDA read APIs backed by the shared profiling service."""

    def __init__(self, *, profile_service: DatasetProfileService) -> None:
        self.profile_service = profile_service

    def get_profile(self, source_id: str) -> EDAProfileResponse:
        profile = self.profile_service.build_profile(source_id)
        return EDAProfileResponse.model_validate(profile.model_dump())
