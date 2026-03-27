from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
from .service import VisualizationService


def build_visualization_service(
    *,
    repository: DatasetRepository,
    reader: DatasetReader,
) -> VisualizationService:
    return VisualizationService(repository=repository, reader=reader)
