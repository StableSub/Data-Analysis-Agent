from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ..datasets.dependencies import get_dataset_reader, get_dataset_repository
from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
from ..results.repository import ResultsRepository
from ..visualization.dependencies import get_visualization_service
from ..visualization.service import VisualizationService
from .processor import AnalysisProcessor
from .run_service import AnalysisRunService
from .sandbox import AnalysisSandbox
from .service import AnalysisService


def build_analysis_processor() -> AnalysisProcessor:
    return AnalysisProcessor()


def get_analysis_processor() -> AnalysisProcessor:
    return build_analysis_processor()


def build_analysis_run_service(*, default_model: str = "gpt-5-nano") -> AnalysisRunService:
    return AnalysisRunService(default_model=default_model)


def get_analysis_run_service() -> AnalysisRunService:
    return build_analysis_run_service()


def build_analysis_sandbox(*, timeout_seconds: int = 15) -> AnalysisSandbox:
    return AnalysisSandbox(timeout_seconds=timeout_seconds)


def get_analysis_sandbox() -> AnalysisSandbox:
    return build_analysis_sandbox()


def build_results_repository(*, db: Session) -> ResultsRepository:
    return ResultsRepository(db)


def get_results_repository(db: Session = Depends(get_db)) -> ResultsRepository:
    return build_results_repository(db=db)


def build_analysis_service(
    *,
    repository: DatasetRepository,
    reader: DatasetReader,
    processor: AnalysisProcessor,
    run_service: AnalysisRunService,
    sandbox: AnalysisSandbox,
    results_repository: ResultsRepository | None = None,
    visualization_service: VisualizationService | None = None,
) -> AnalysisService:
    return AnalysisService(
        dataset_repository=repository,
        dataset_reader=reader,
        run_service=run_service,
        processor=processor,
        sandbox=sandbox,
        results_repository=results_repository,
        visualization_service=visualization_service,
    )


def get_analysis_service(
    repository: DatasetRepository = Depends(get_dataset_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
    processor: AnalysisProcessor = Depends(get_analysis_processor),
    run_service: AnalysisRunService = Depends(get_analysis_run_service),
    sandbox: AnalysisSandbox = Depends(get_analysis_sandbox),
    results_repository: ResultsRepository = Depends(get_results_repository),
    visualization_service: VisualizationService = Depends(get_visualization_service),
) -> AnalysisService:
    return build_analysis_service(
        repository=repository,
        reader=reader,
        processor=processor,
        run_service=run_service,
        sandbox=sandbox,
        results_repository=results_repository,
        visualization_service=visualization_service,
    )
