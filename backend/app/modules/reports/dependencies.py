from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ..datasets.dependencies import get_data_source_repository, get_dataset_reader
from ..datasets.repository import DataSourceRepository
from ..datasets.service import DatasetReader
from .repository import ReportRepository
from .service import ReportService


def build_report_repository(db: Session) -> ReportRepository:
    return ReportRepository(db)


def get_report_repository(db: Session = Depends(get_db)) -> ReportRepository:
    return build_report_repository(db)


def build_report_service(
    *,
    repository: ReportRepository,
    dataset_repository: DataSourceRepository,
    reader: DatasetReader,
) -> ReportService:
    return ReportService(
        repository,
        dataset_repository=dataset_repository,
        reader=reader,
    )


def get_report_service(
    repository: ReportRepository = Depends(get_report_repository),
    dataset_repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> ReportService:
    return build_report_service(
        repository=repository,
        dataset_repository=dataset_repository,
        reader=reader,
    )
