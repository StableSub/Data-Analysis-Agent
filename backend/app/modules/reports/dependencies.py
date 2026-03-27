from sqlalchemy.orm import Session

from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetReader
from .repository import ReportRepository
from .service import ReportService


def build_report_repository(db: Session) -> ReportRepository:
    return ReportRepository(db)


def build_report_service(
    *,
    repository: ReportRepository,
    dataset_repository: DatasetRepository,
    reader: DatasetReader,
) -> ReportService:
    return ReportService(
        repository,
        dataset_repository=dataset_repository,
        reader=reader,
    )
