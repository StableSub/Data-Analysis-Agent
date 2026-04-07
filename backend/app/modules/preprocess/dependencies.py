from fastapi import Depends

from ..datasets.dependencies import get_dataset_reader, get_dataset_repository
from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
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
    repository: DatasetRepository,
    reader: DatasetReader,
    processor: PreprocessProcessor,
    profile_service: DatasetProfileService,
) -> PreprocessService:
    return PreprocessService(
        repository=repository,
        reader=reader,
        processor=processor,
        profile_service=profile_service,
    )


def get_preprocess_service(
    repository: DatasetRepository = Depends(get_dataset_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
    processor: PreprocessProcessor = Depends(get_preprocess_processor),
    profile_service: DatasetProfileService = Depends(get_dataset_profile_service),
) -> PreprocessService:
    return build_preprocess_service(
        repository=repository,
        reader=reader,
        processor=processor,
        profile_service=profile_service,
    )
