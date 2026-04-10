from fastapi import Depends

from ..datasets.dependencies import get_dataset_reader, get_dataset_repository
from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
from .service import VisualizationService


def build_visualization_service(
    *,
    repository: DatasetRepository,
    reader: DatasetReader,
) -> VisualizationService:
    return VisualizationService(repository=repository, reader=reader)


def get_visualization_service(
    repository: DatasetRepository = Depends(get_dataset_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> VisualizationService:
    return build_visualization_service(repository=repository, reader=reader)
