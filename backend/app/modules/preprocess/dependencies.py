from fastapi import Depends

from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader, get_data_source_repository, get_dataset_reader
from ..eda.dependencies import get_eda_service
from ..eda.service import EDAService
from ..profiling.dependencies import get_dataset_profile_service
from ..profiling.service import DatasetProfileService
from .processor import PreprocessProcessor
from .service import PreprocessService


def build_preprocess_processor() -> PreprocessProcessor:
    return PreprocessProcessor()


def get_preprocess_processor() -> PreprocessProcessor:
    return build_preprocess_processor()


def build_preprocess_service(
    *,
    repository: DataSourceRepository,
    reader: DatasetReader,
    processor: PreprocessProcessor,
    profile_service: DatasetProfileService,
    eda_service: EDAService,
) -> PreprocessService:
    return PreprocessService(
        repository=repository,
        reader=reader,
        processor=processor,
        profile_service=profile_service,
        eda_service=eda_service,
    )


def get_preprocess_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
    processor: PreprocessProcessor = Depends(get_preprocess_processor),
    profile_service: DatasetProfileService = Depends(get_dataset_profile_service),
    eda_service: EDAService = Depends(get_eda_service),
) -> PreprocessService:
    return build_preprocess_service(
        repository=repository,
        reader=reader,
        processor=processor,
        profile_service=profile_service,
        eda_service=eda_service,
    )
