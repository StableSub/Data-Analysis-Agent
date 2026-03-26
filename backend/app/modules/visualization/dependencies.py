from fastapi import Depends

from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader, get_data_source_repository, get_dataset_reader
from .service import VisualizationService


def build_visualization_service(
    *,
    repository: DataSourceRepository,
    reader: DatasetReader,
) -> VisualizationService:
    return VisualizationService(repository=repository, reader=reader)


def get_visualization_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> VisualizationService:
    return build_visualization_service(repository=repository, reader=reader)
