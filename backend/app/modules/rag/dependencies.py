from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...orchestration.dependencies import get_agent
from ..datasets.repository import DataSourceRepository
from .repository import RagRepository
from .service import RagService


def _vector_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "vectors"


@lru_cache(maxsize=1)
def get_embedder():
    from .infra.embedding import E5Embedder

    return E5Embedder()


def get_rag_repository(db: Session = Depends(get_db)) -> RagRepository:
    return RagRepository(db)


def get_rag_service(
    db: Session = Depends(get_db),
    repository: RagRepository = Depends(get_rag_repository),
    agent=Depends(get_agent),
) -> RagService:
    dataset_repository = DataSourceRepository(db)
    return RagService(
        repository=repository,
        storage_dir=_vector_storage_dir(),
        embedder=get_embedder(),
        dataset_repository=dataset_repository,
        answer_agent=agent,
    )
