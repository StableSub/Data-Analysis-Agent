from fastapi import Depends

from ..datasets.dependencies import get_data_source_repository, get_dataset_reader
from ..datasets.reader import DatasetReader
from ..datasets.repository import DataSourceRepository
from .processor import PreprocessProcessor
from .service import PreprocessService


def get_preprocess_processor() -> PreprocessProcessor:
    return PreprocessProcessor()


def get_preprocess_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
    processor: PreprocessProcessor = Depends(get_preprocess_processor),
) -> PreprocessService:
    return PreprocessService(repository=repository, reader=reader, processor=processor)
