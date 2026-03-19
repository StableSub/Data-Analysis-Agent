from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ..datasets.dependencies import get_data_source_repository, get_dataset_reader
from ..datasets.reader import DatasetReader
from ..datasets.repository import DataSourceRepository
from .repository import ReportRepository
from .service import ReportService


def get_report_repository(db: Session = Depends(get_db)) -> ReportRepository:
    return ReportRepository(db)


def get_report_service(
    repository: ReportRepository = Depends(get_report_repository),
    dataset_repository: DataSourceRepository = Depends(get_data_source_repository),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> ReportService:
    return ReportService(
        repository,
        dataset_repository=dataset_repository,
        reader=reader,
    )
