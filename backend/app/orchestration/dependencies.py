from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from ..modules.datasets.dependencies import (
    build_data_source_repository,
    build_dataset_reader,
)
from ..modules.preprocess.dependencies import (
    build_preprocess_processor,
    build_preprocess_service,
)
from ..modules.preprocess.service import PreprocessService
from ..modules.rag.dependencies import build_rag_repository, build_rag_service
from ..modules.rag.service import RagService
from ..modules.reports.dependencies import build_report_repository, build_report_service
from ..modules.reports.service import ReportService
from ..modules.visualization.dependencies import build_visualization_service
from ..modules.visualization.service import VisualizationService

if TYPE_CHECKING:
    from .client import AgentClient


@dataclass(frozen=True)
class WorkflowServices:
    preprocess_service: PreprocessService
    rag_service: RagService
    visualization_service: VisualizationService
    report_service: ReportService


@lru_cache(maxsize=1)
def get_agent() -> "AgentClient":
    from .client import AgentClient

    return AgentClient()


def _bundle_workflow_services(
    *,
    preprocess_service: PreprocessService,
    rag_service: RagService,
    visualization_service: VisualizationService,
    report_service: ReportService,
) -> WorkflowServices:
    return WorkflowServices(
        preprocess_service=preprocess_service,
        rag_service=rag_service,
        visualization_service=visualization_service,
        report_service=report_service,
    )


def build_orchestration_services(*, db: Session, agent: Any) -> WorkflowServices:
    dataset_repository = build_data_source_repository(db)
    dataset_reader = build_dataset_reader()
    preprocess_service = build_preprocess_service(
        repository=dataset_repository,
        reader=dataset_reader,
        processor=build_preprocess_processor(),
    )
    rag_service = build_rag_service(
        repository=build_rag_repository(db),
        dataset_repository=dataset_repository,
        answer_agent=agent,
    )
    visualization_service = build_visualization_service(
        repository=dataset_repository,
        reader=dataset_reader,
    )
    report_service = build_report_service(
        repository=build_report_repository(db),
        dataset_repository=dataset_repository,
        reader=dataset_reader,
    )
    return _bundle_workflow_services(
        preprocess_service=preprocess_service,
        rag_service=rag_service,
        visualization_service=visualization_service,
        report_service=report_service,
    )
