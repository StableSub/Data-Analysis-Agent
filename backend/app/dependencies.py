from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from .core.db import get_db
from .domain.chat.repository import ChatRepository
from .domain.chat.service import ChatService
from .domain.data_source.repository import DataSourceRepository
from .domain.guideline.repository import GuidelineRepository
from .ai.agents.client import AgentClient
from .rag.core.embedding import E5Embedder
from .rag.guideline_repository import GuidelineRagRepository
from .rag.repository import RagRepository
from .rag.service import GuidelineRagService, RagService


def get_chat_repository(db=Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)

def get_data_source_repository(db=Depends(get_db)) -> DataSourceRepository:
    return DataSourceRepository(db)

@lru_cache(maxsize=1)
def get_agent() -> AgentClient:
    return AgentClient()

@lru_cache(maxsize=1)
def get_embedder() -> E5Embedder:
    return E5Embedder()

def get_rag_repository(db=Depends(get_db)) -> RagRepository:
    return RagRepository(db)

def get_rag_service(
    repository: RagRepository = Depends(get_rag_repository),
) -> RagService:
    storage: Path = Path("storage") / "vectors"
    return RagService(
        repository=repository,
        storage_dir=storage,
        embedder=get_embedder(),
    )

def get_guideline_repository(db=Depends(get_db)) -> GuidelineRepository:
    return GuidelineRepository(db)

def get_guideline_rag_repository(db=Depends(get_db)) -> GuidelineRagRepository:
    return GuidelineRagRepository(db)

def get_guideline_rag_service(
    repository: GuidelineRagRepository = Depends(get_guideline_rag_repository),
) -> GuidelineRagService:
    storage: Path = Path("storage") / "guideline_vectors"
    return GuidelineRagService(
        repository=repository,
        storage_dir=storage,
        embedder=get_embedder(),
    )

def get_chat_service(
    repository: ChatRepository = Depends(get_chat_repository),
    data_source_repository: DataSourceRepository = Depends(get_data_source_repository),
) -> ChatService:
    return ChatService(
        agent=get_agent(),
        repository=repository,
        data_source_repository=data_source_repository,
    )
