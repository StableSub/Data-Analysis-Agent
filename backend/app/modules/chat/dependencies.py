from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from ...orchestration.client import AgentClient
from ...orchestration.dependencies import get_agent
from ..datasets.dependencies import get_data_source_repository
from ..datasets.repository import DataSourceRepository
from .repository import ChatRepository
from .run_service import ChatRunService
from .service import ChatService
from .session_service import ChatSessionService


def get_chat_repository(db: Session = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


def get_chat_session_service(
    repository: ChatRepository = Depends(get_chat_repository),
) -> ChatSessionService:
    return ChatSessionService(repository)


def get_chat_run_service(
    agent: AgentClient = Depends(get_agent),
    repository: ChatRepository = Depends(get_chat_repository),
    session_service: ChatSessionService = Depends(get_chat_session_service),
    data_source_repository: DataSourceRepository = Depends(get_data_source_repository),
) -> ChatRunService:
    return ChatRunService(
        agent=agent,
        repository=repository,
        session_service=session_service,
        data_source_repository=data_source_repository,
    )


def get_chat_service(
    session_service: ChatSessionService = Depends(get_chat_session_service),
    run_service: ChatRunService = Depends(get_chat_run_service),
) -> ChatService:
    return ChatService(session_service=session_service, run_service=run_service)
