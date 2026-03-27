from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...orchestration.client import AgentClient
from ...orchestration.dependencies import get_agent_client
from ..datasets.dependencies import get_dataset_repository
from ..datasets.repository import DatasetRepository
from .repository import ChatRepository
from .service import ChatService


def get_chat_repository(db: Session = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


def get_chat_service(
    agent: AgentClient = Depends(get_agent_client),
    repository: ChatRepository = Depends(get_chat_repository),
    dataset_repository: DatasetRepository = Depends(get_dataset_repository),
) -> ChatService:
    return ChatService(
        agent=agent,
        repository=repository,
        dataset_repository=dataset_repository,
    )
