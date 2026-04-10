from sqlalchemy.orm import Session

from .repository import ReportRepository
from .service import ReportService


def build_report_repository(db: Session) -> ReportRepository:
    return ReportRepository(db)


def build_report_service(
    *,
    repository: ReportRepository,
) -> ReportService:
    return ReportService(
        repository,
    )
