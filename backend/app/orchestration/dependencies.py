from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import Depends
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..modules.datasets.dependencies import build_dataset_reader, build_dataset_repository
from ..modules.guidelines.dependencies import build_guideline_repository, build_guideline_service
from ..modules.guidelines.service import GuidelineService
from ..modules.preprocess.dependencies import (
    build_preprocess_processor,
    build_preprocess_service,
)
from ..modules.preprocess.service import PreprocessService
from ..modules.rag.dependencies import (
    build_guideline_rag_repository,
    build_guideline_rag_service,
    build_rag_repository,
    build_rag_service,
)
from ..modules.rag.service import GuidelineRagService, RagService
from ..modules.reports.dependencies import build_report_repository, build_report_service
from ..modules.reports.service import ReportService
from ..modules.visualization.dependencies import build_visualization_service
from ..modules.visualization.service import VisualizationService

if TYPE_CHECKING:
    from .client import AgentClient

CHECKPOINT_DB_PATH = Path(__file__).resolve().parents[3] / "storage" / "langgraph_checkpoints.db"


@dataclass(frozen=True)
class WorkflowServices:
    preprocess_service: PreprocessService
    rag_service: RagService
    guideline_service: GuidelineService
    guideline_rag_service: GuidelineRagService
    visualization_service: VisualizationService
    report_service: ReportService


def build_orchestration_services(*, db: Session, agent: Any) -> WorkflowServices:
    dataset_repository = build_dataset_repository(db)
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
    guideline_service = build_guideline_service(
        repository=build_guideline_repository(db),
    )
    guideline_rag_service = build_guideline_rag_service(
        repository=build_guideline_rag_repository(db),
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
    return WorkflowServices(
        preprocess_service=preprocess_service,
        rag_service=rag_service,
        guideline_service=guideline_service,
        guideline_rag_service=guideline_rag_service,
        visualization_service=visualization_service,
        report_service=report_service,
    )


def build_agent_client(*, db: Session) -> "AgentClient":
    from .builder import build_main_workflow
    from .client import AgentClient

    agent_box: dict[str, AgentClient] = {}

    @asynccontextmanager
    async def workflow_runtime_factory():
        agent = agent_box["agent"]
        services = build_orchestration_services(db=db, agent=agent)
        CHECKPOINT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH)) as checkpointer:
            workflow = build_main_workflow(
                preprocess_service=services.preprocess_service,
                rag_service=services.rag_service,
                guideline_service=services.guideline_service,
                guideline_rag_service=services.guideline_rag_service,
                visualization_service=services.visualization_service,
                report_service=services.report_service,
                default_model=agent.default_model,
                checkpointer=checkpointer,
            )
            yield workflow

    agent = AgentClient(
        workflow_runtime_factory=workflow_runtime_factory,
    )
    agent_box["agent"] = agent
    return agent


def get_agent_client(db: Session = Depends(get_db)) -> "AgentClient":
    return build_agent_client(db=db)
