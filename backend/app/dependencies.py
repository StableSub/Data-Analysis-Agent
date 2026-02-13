import os
from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from .core.db import get_db
from .domain.chat.repository import ChatRepository
from .domain.chat.service import ChatService
from .ai.agents.client import AgentClient
from .rag.core.embedding import E5Embedder
from .rag.repository import RagRepository
from .rag.service import RagService


def get_chat_repository(db=Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)

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

def get_chat_service(
    repository: ChatRepository = Depends(get_chat_repository),
) -> ChatService:
    return ChatService(
        agent=get_agent(),
        repository=repository,
    )
