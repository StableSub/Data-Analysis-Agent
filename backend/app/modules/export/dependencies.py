from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ..results.repository import ResultsRepository
from .service import ExportService


def get_results_repository(db: Session = Depends(get_db)) -> ResultsRepository:
    return ResultsRepository(db)


def get_export_service(
    results_repository: ResultsRepository = Depends(get_results_repository),
) -> ExportService:
    return ExportService(results_repository)
