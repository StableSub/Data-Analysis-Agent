from fastapi import Depends

from ..profiling.dependencies import get_dataset_profile_service
from ..profiling.service import DatasetProfileService
from .service import EDAService


def build_eda_service(*, profile_service: DatasetProfileService) -> EDAService:
    return EDAService(profile_service=profile_service)


def get_eda_service(
    profile_service: DatasetProfileService = Depends(get_dataset_profile_service),
) -> EDAService:
    return build_eda_service(profile_service=profile_service)
