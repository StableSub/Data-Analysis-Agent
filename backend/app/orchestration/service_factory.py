from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from ..modules.datasets.reader import DatasetReader
from ..modules.datasets.repository import DataSourceRepository
from ..modules.preprocess.processor import PreprocessProcessor
from ..modules.preprocess.service import PreprocessService
from ..modules.rag.repository import RagRepository
from ..modules.rag.service import RagService
from ..modules.reports.repository import ReportRepository
from ..modules.reports.service import ReportService
from ..modules.visualization.service import VisualizationService

if TYPE_CHECKING:
    from .client import AgentClient


@lru_cache(maxsize=1)
def get_agent() -> "AgentClient":
    from .client import AgentClient

    return AgentClient()


@lru_cache(maxsize=1)
def get_embedder():
    from ..modules.rag.infra.embedding import E5Embedder

    return E5Embedder()


@dataclass(frozen=True)
class WorkflowServices:
    preprocess_service: PreprocessService
    rag_service: RagService
    visualization_service: VisualizationService
    report_service: ReportService


def build_workflow_services(*, db: Session, agent: Any) -> WorkflowServices:
    dataset_repository = DataSourceRepository(db)
    dataset_reader = DatasetReader()
    rag_service = RagService(
        repository=RagRepository(db),
        storage_dir=Path(__file__).resolve().parents[3] / "storage" / "vectors",
        embedder=get_embedder(),
        dataset_repository=dataset_repository,
        answer_agent=agent,
    )
    return WorkflowServices(
        preprocess_service=PreprocessService(
            repository=dataset_repository,
            reader=dataset_reader,
            processor=PreprocessProcessor(),
        ),
        rag_service=rag_service,
        visualization_service=VisualizationService(
            repository=dataset_repository,
            reader=dataset_reader,
        ),
        report_service=ReportService(
            ReportRepository(db),
            dataset_repository=dataset_repository,
            reader=dataset_reader,
        ),
    )
