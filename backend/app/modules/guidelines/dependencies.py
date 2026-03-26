from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from .repository import GuidelineRepository
from .service import GuidelineService


def _guidelines_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "guidelines"


def build_guideline_repository(db: Session) -> GuidelineRepository:
    return GuidelineRepository(db)


def get_guideline_repository(db: Session = Depends(get_db)) -> GuidelineRepository:
    return build_guideline_repository(db)


def build_guideline_service(*, repository: GuidelineRepository) -> GuidelineService:
    return GuidelineService(
        repository=repository,
        storage_dir=_guidelines_storage_dir(),
    )


def get_guideline_service(
    repository: GuidelineRepository = Depends(get_guideline_repository),
) -> GuidelineService:
    return build_guideline_service(repository=repository)
