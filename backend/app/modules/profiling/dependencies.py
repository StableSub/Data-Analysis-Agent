from fastapi import Depends

from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader, get_data_source_repository, get_dataset_reader
from .service import DatasetProfileService


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
