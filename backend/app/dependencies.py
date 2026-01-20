import os
from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from .core.db import get_db
from .domain.chat.repository import ChatRepository
from .domain.chat.service import ChatService
from .domain.data_source.repository import DataSourceRepository
from .ai.orchestrator.chat_flow import ChatFlowOrchestrator
from .ai.llm.client import LLMClient
from .rag.core.embedding import E5Embedder
from .rag.repository import RagRepository
from .rag.service import RagService


def get_chat_repository(db=Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


def get_data_source_repository(db=Depends(get_db)) -> DataSourceRepository:
    return DataSourceRepository(db)


def get_llm_client() -> LLMClient:
    """
    환경변수 LLM_PRESET 에서 프리셋을 읽어 LLMClient를 생성합니다.
    기본값은 gemini_flash입니다.
    """
    preset = os.getenv("LLM_PRESET", "gemini_flash")
    return LLMClient(preset=preset)


@lru_cache(maxsize=1)
def get_embedder() -> E5Embedder:
    return E5Embedder()


def get_rag_repository(db=Depends(get_db)) -> RagRepository:
    return RagRepository(db)


def get_rag_service(
    repository: RagRepository = Depends(get_rag_repository),
    llm_client: LLMClient = Depends(get_llm_client),
) -> RagService:
    storage: Path = Path("storage") / "vectors"
    return RagService(
        repository=repository,
        storage_dir=storage,
        embedder=get_embedder(),
        llm_client=llm_client,
    )


def get_orchestrator(
    llm_client: LLMClient = Depends(get_llm_client),
) -> ChatFlowOrchestrator:
    return ChatFlowOrchestrator(llm_client=llm_client)


def get_chat_service(
    repository: ChatRepository = Depends(get_chat_repository),
    orchestrator: ChatFlowOrchestrator = Depends(get_orchestrator),
    data_source_repository: DataSourceRepository = Depends(get_data_source_repository),
    rag_service: RagService = Depends(get_rag_service),
) -> ChatService:
    return ChatService(
        repository=repository,
        orchestrator=orchestrator,
        data_source_repository=data_source_repository,
        rag_service=rag_service,
    )
