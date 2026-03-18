from fastapi import Depends

from ..datasets.dependencies import get_data_source_repository, get_dataset_reader
from ..datasets.reader import DatasetReader
from ..datasets.repository import DataSourceRepository
from .service import VisualizationService


def get_visualization_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> VisualizationService:
    return VisualizationService(repository=repository, reader=reader)
