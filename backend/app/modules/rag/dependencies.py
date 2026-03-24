from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ..datasets.repository import DataSourceRepository
from .guideline_repository import GuidelineRagRepository
from .repository import RagRepository
from .service import GuidelineRagService, RagService


def _vector_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "vectors"


def _guideline_vector_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "guideline_vectors"


@lru_cache(maxsize=1)
def get_embedder():
    from .infra.embedding import E5Embedder

    return E5Embedder()


def build_rag_repository(db: Session) -> RagRepository:
    return RagRepository(db)


def get_rag_repository(db: Session = Depends(get_db)) -> RagRepository:
    return build_rag_repository(db)


def build_rag_service(
    *,
    repository: RagRepository,
    dataset_repository: DataSourceRepository,
    answer_agent=None,
) -> RagService:
    return RagService(
        repository=repository,
        storage_dir=_vector_storage_dir(),
        embedder=get_embedder(),
        dataset_repository=dataset_repository,
        answer_agent=answer_agent,
    )


def get_rag_service(
    db: Session = Depends(get_db),
    repository: RagRepository = Depends(get_rag_repository),
) -> RagService:
    dataset_repository = DataSourceRepository(db)
    return build_rag_service(
        repository=repository,
        dataset_repository=dataset_repository,
    )


def build_guideline_rag_repository(db: Session) -> GuidelineRagRepository:
    return GuidelineRagRepository(db)


def get_guideline_rag_repository(db: Session = Depends(get_db)) -> GuidelineRagRepository:
    return build_guideline_rag_repository(db)


def build_guideline_rag_service(
    *,
    repository: GuidelineRagRepository,
) -> GuidelineRagService:
    return GuidelineRagService(
        repository=repository,
        storage_dir=_guideline_vector_storage_dir(),
        embedder=get_embedder(),
    )


def get_guideline_rag_service(
    repository: GuidelineRagRepository = Depends(get_guideline_rag_repository),
) -> GuidelineRagService:
    return build_guideline_rag_service(repository=repository)
