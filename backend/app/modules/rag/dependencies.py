from functools import lru_cache
from pathlib import Path
from typing import Protocol

from fastapi import Depends
import numpy as np
from numpy.typing import NDArray
from sqlalchemy.orm import Session

from ...core.db import get_db
from ..datasets.dependencies import get_dataset_repository, get_dataset_service
from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetService
from ..guidelines.dependencies import get_guideline_service
from ..guidelines.service import GuidelineService
from .guideline_repository import GuidelineRagRepository
from .repository import RagRepository
from .service import DatasetRagSyncService, GuidelineRagService, GuidelineRagSyncService, RagService


def _vector_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "vectors"


def _guideline_vector_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "guideline_vectors"


class Embedder(Protocol):
    model_name: str
    embedding_dim: int

    def embed_documents(self, texts: list[str]) -> NDArray[np.float32]:
        ...

    def embed_query(self, query: str) -> NDArray[np.float32]:
        ...


class LazyEmbedder:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        self.model_name: str = model_name
        self._delegate: Embedder | None = None

    @property
    def embedding_dim(self) -> int:
        return self._get_delegate().embedding_dim

    def embed_documents(self, texts: list[str]) -> NDArray[np.float32]:
        return self._get_delegate().embed_documents(texts)

    def embed_query(self, query: str) -> NDArray[np.float32]:
        return self._get_delegate().embed_query(query)

    def _get_delegate(self) -> Embedder:
        if self._delegate is None:
            from .infra.embedding import E5Embedder

            self._delegate = E5Embedder(self.model_name)
        return self._delegate


@lru_cache(maxsize=1)
def get_embedder() -> LazyEmbedder:
    return LazyEmbedder()


def build_rag_repository(db: Session) -> RagRepository:
    return RagRepository(db)


def get_rag_repository(db: Session = Depends(get_db)) -> RagRepository:
    return build_rag_repository(db)


def build_rag_service(
    *,
    repository: RagRepository,
    dataset_repository: DatasetRepository,
    answer_agent: object | None = None,
    storage_dir: Path | None = None,
) -> RagService:
    return RagService(
        repository=repository,
        storage_dir=storage_dir or _vector_storage_dir(),
        embedder=get_embedder(),
        dataset_repository=dataset_repository,
        answer_agent=answer_agent,
    )


def get_rag_service(
    repository: RagRepository = Depends(get_rag_repository),
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
) -> RagService:
    return build_rag_service(
        repository=repository,
        dataset_repository=dataset_repository,
    )


def build_dataset_rag_sync_service(
    *,
    dataset_service: DatasetService,
    rag_service: RagService,
) -> DatasetRagSyncService:
    return DatasetRagSyncService(
        dataset_service=dataset_service,
        rag_service=rag_service,
    )


def get_dataset_rag_sync_service(
    dataset_service: DatasetService = Depends(get_dataset_service),
    rag_service: RagService = Depends(get_rag_service),
) -> DatasetRagSyncService:
    return build_dataset_rag_sync_service(
        dataset_service=dataset_service,
        rag_service=rag_service,
    )


def build_guideline_rag_repository(db: Session) -> GuidelineRagRepository:
    return GuidelineRagRepository(db)


def get_guideline_rag_repository(db: Session = Depends(get_db)) -> GuidelineRagRepository:
    return build_guideline_rag_repository(db)


def build_guideline_rag_service(
    *,
    repository: GuidelineRagRepository,
    storage_dir: Path | None = None,
) -> GuidelineRagService:
    return GuidelineRagService(
        repository=repository,
        storage_dir=storage_dir or _guideline_vector_storage_dir(),
        embedder=get_embedder(),
    )


def get_guideline_rag_service(
    repository: GuidelineRagRepository = Depends(get_guideline_rag_repository),
) -> GuidelineRagService:
    return build_guideline_rag_service(repository=repository)


def build_guideline_rag_sync_service(
    *,
    guideline_service: GuidelineService,
    guideline_rag_service: GuidelineRagService,
) -> GuidelineRagSyncService:
    return GuidelineRagSyncService(
        guideline_service=guideline_service,
        guideline_rag_service=guideline_rag_service,
    )


def get_guideline_rag_sync_service(
    guideline_service: GuidelineService = Depends(get_guideline_service),
    guideline_rag_service: GuidelineRagService = Depends(get_guideline_rag_service),
) -> GuidelineRagSyncService:
    return build_guideline_rag_sync_service(
        guideline_service=guideline_service,
        guideline_rag_service=guideline_rag_service,
    )
