from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from fastapi import Depends
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..modules.datasets.service import build_data_source_repository, build_dataset_reader
from ..modules.eda.dependencies import build_eda_service
from ..modules.eda.service import EDAService
from ..modules.analysis.dependencies import (
    build_analysis_processor,
    build_analysis_run_service,
    build_analysis_sandbox,
    build_analysis_service,
    build_results_repository,
)
from ..modules.analysis.service import AnalysisService
from ..modules.datasets.service import (
    build_data_source_repository,
    build_dataset_reader,
)
from ..modules.preprocess.dependencies import (
    build_preprocess_processor,
    build_preprocess_service,
)
from ..modules.preprocess.service import PreprocessService
from ..modules.profiling.dependencies import build_dataset_profile_service
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
    analysis_service: AnalysisService
    preprocess_service: PreprocessService
    eda_service: EDAService
    rag_service: RagService
    visualization_service: VisualizationService
    report_service: ReportService


@lru_cache(maxsize=1)
def get_workflow_checkpointer() -> InMemorySaver:
    return InMemorySaver()


def build_orchestration_services(*, db: Session, agent: Any) -> WorkflowServices:
    dataset_repository = build_data_source_repository(db)
    dataset_reader = build_dataset_reader()
    profile_service = build_dataset_profile_service(
        repository=dataset_repository,
        reader=dataset_reader,
    )
    eda_service = build_eda_service(
        profile_service=profile_service,
        dataset_repository=dataset_repository,
        reader=dataset_reader,
    )
    visualization_service = build_visualization_service(
        repository=dataset_repository,
        reader=dataset_reader,
    )
    analysis_service = build_analysis_service(
        repository=dataset_repository,
        reader=dataset_reader,
        processor=build_analysis_processor(),
        run_service=build_analysis_run_service(),
        sandbox=build_analysis_sandbox(),
        results_repository=build_results_repository(db=db),
        visualization_service=visualization_service,
    )
    preprocess_service = build_preprocess_service(
        repository=dataset_repository,
        reader=dataset_reader,
        processor=build_preprocess_processor(),
        profile_service=profile_service,
    )
    rag_service = build_rag_service(
        repository=build_rag_repository(db),
        dataset_repository=dataset_repository,
        answer_agent=agent,
    )
    report_service = build_report_service(
        repository=build_report_repository(db),
        dataset_repository=dataset_repository,
        reader=dataset_reader,
    )
    return WorkflowServices(
        analysis_service=analysis_service,
        preprocess_service=preprocess_service,
        eda_service=eda_service,
        rag_service=rag_service,
        visualization_service=visualization_service,
        report_service=report_service,
    )


def build_agent_client(*, db: Session) -> "AgentClient":
    from .builder import build_main_workflow
    from .client import AgentClient

    checkpointer = get_workflow_checkpointer()
    agent_box: dict[str, AgentClient] = {}

    @contextmanager
    def workflow_runtime_factory():
        agent = agent_box["agent"]
        services = build_orchestration_services(db=db, agent=agent)
        workflow = build_main_workflow(
            db=db,
            analysis_service=services.analysis_service,
            preprocess_service=services.preprocess_service,
            eda_service=services.eda_service,
            rag_service=services.rag_service,
            visualization_service=services.visualization_service,
            report_service=services.report_service,
            default_model=agent.default_model,
            checkpointer=checkpointer,
        )
        yield workflow

    agent = AgentClient(
        workflow_runtime_factory=workflow_runtime_factory,
        checkpointer=checkpointer,
    )
    agent_box["agent"] = agent
    return agent


def get_agent_client(db: Session = Depends(get_db)) -> "AgentClient":
    return build_agent_client(db=db)
