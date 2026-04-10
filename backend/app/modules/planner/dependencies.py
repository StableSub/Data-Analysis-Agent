from fastapi import Depends

from ..analysis.processor import AnalysisProcessor
from ..profiling.dependencies import get_dataset_context_service
from ..profiling.service import DatasetContextService
from .service import PlannerService


def build_planner_service(
    *,
    dataset_context_service: DatasetContextService,
    analysis_processor: AnalysisProcessor | None = None,
    default_model: str = "gpt-5-nano",
) -> PlannerService:
    return PlannerService(
        dataset_context_service=dataset_context_service,
        analysis_processor=analysis_processor or AnalysisProcessor(),
        default_model=default_model,
    )


def get_planner_service(
    dataset_context_service: DatasetContextService = Depends(get_dataset_context_service),
) -> PlannerService:
    return build_planner_service(dataset_context_service=dataset_context_service)
