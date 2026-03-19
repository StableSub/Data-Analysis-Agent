from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.agent_protocols import ApprovalAwareTraceStreamingAgent
from ...core.db import get_db
from ...orchestration.service_factory import get_agent
from ..datasets.dependencies import get_data_source_repository
from ..datasets.repository import DataSourceRepository
from .repository import ChatRepository
from .service import ChatService


def get_chat_repository(db: Session = Depends(get_db)) -> ChatRepository:
    return ChatRepository(db)


def get_chat_service(
    agent: ApprovalAwareTraceStreamingAgent = Depends(get_agent),
    repository: ChatRepository = Depends(get_chat_repository),
    data_source_repository: DataSourceRepository = Depends(get_data_source_repository),
) -> ChatService:
    return ChatService(
        agent=agent,
        repository=repository,
        data_source_repository=data_source_repository,
    )
