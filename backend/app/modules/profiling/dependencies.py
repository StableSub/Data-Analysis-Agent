from fastapi import Depends

from ..datasets.dependencies import get_data_source_repository, get_dataset_reader
from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader
from .service import DatasetContextService, DatasetProfileService


def build_dataset_profile_service(
    *,
    repository: DataSourceRepository,
    reader: DatasetReader,
) -> DatasetProfileService:
    return DatasetProfileService(repository=repository, reader=reader)


def get_dataset_profile_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> DatasetProfileService:
    return build_dataset_profile_service(repository=repository, reader=reader)


def build_dataset_context_service(
    *,
    repository: DataSourceRepository,
    profile_service: DatasetProfileService,
) -> DatasetContextService:
    return DatasetContextService(
        repository=repository,
        profile_service=profile_service,
    )


def get_dataset_context_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    profile_service: DatasetProfileService = Depends(get_dataset_profile_service),
) -> DatasetContextService:
    return build_dataset_context_service(
        repository=repository,
        profile_service=profile_service,
    )
