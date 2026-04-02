from fastapi import Depends

from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader, get_data_source_repository, get_dataset_reader
from ..profiling.dependencies import get_dataset_profile_service
from ..profiling.service import DatasetProfileService
from .service import EDAService


def build_eda_service(
    *,
    profile_service: DatasetProfileService,
    dataset_repository: DataSourceRepository,
    reader: DatasetReader,
) -> EDAService:
    return EDAService(
        profile_service=profile_service,
        dataset_repository=dataset_repository,
        reader=reader,
    )


def get_eda_service(
    profile_service: DatasetProfileService = Depends(get_dataset_profile_service),
    dataset_repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> EDAService:
    return build_eda_service(
        profile_service=profile_service,
        dataset_repository=dataset_repository,
        reader=reader,
    )
