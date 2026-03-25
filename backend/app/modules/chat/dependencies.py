from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...orchestration.client import AgentClient
from ...orchestration.dependencies import get_agent_client
from ..datasets.repository import DataSourceRepository
from ..datasets.service import get_data_source_repository
from .repository import ChatRepository
from .service import ChatService


def get_chat_repository(db: Session = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


def get_chat_service(
    agent: AgentClient = Depends(get_agent_client),
    repository: ChatRepository = Depends(get_chat_repository),
    data_source_repository: DataSourceRepository = Depends(get_data_source_repository),
) -> ChatService:
    return ChatService(
        agent=agent,
        repository=repository,
        data_source_repository=data_source_repository,
    )
