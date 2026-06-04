import asyncio
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.db import Base
from backend.app.modules.chat.models import ChatMessage, ChatSession
from backend.app.modules.chat.repository import ChatRepository
from backend.app.modules.chat.service import ChatService
from backend.app.modules.datasets.repository import DatasetRepository
from backend.app.orchestration.client import AgentClient


def _make_agent() -> AgentClient:
    return AgentClient(workflow_runtime_factory=lambda: None)


def _collect_events(stream: Any) -> list[dict[str, Any]]:
    async def _run() -> list[dict[str, Any]]:
        return [event async for event in stream]

    return asyncio.run(_run())


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_list_sessions_uses_message_timestamps_without_chat_session_timestamp_columns() -> None:
    db = _make_session()
    first_session = ChatSession(title="첫 질문")
    second_session = ChatSession(title=None)
    db.add_all([first_session, second_session])
    db.flush()
    db.add_all(
        [
            ChatMessage(
                session_id=first_session.id,
                role="user",
                content="첫 세션 질문입니다",
                created_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
            ),
            ChatMessage(
                session_id=first_session.id,
                role="assistant",
                content="첫 세션 답변입니다",
                created_at=datetime(2026, 5, 1, 9, 1, tzinfo=timezone.utc),
            ),
            ChatMessage(
                session_id=second_session.id,
                role="user",
                content="두 번째 세션 질문입니다",
                created_at=datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc),
            ),
        ]
    )
    db.commit()

    service = ChatService(
        agent=_make_agent(),
        repository=ChatRepository(db),
        dataset_repository=DatasetRepository(db),
    )

    response = service.list_sessions()

    assert response.total == 2
    assert [item.id for item in response.items] == [second_session.id, first_session.id]
    assert response.items[0].title == "두 번째 세션 질문입니다"
    assert response.items[0].last_message_preview == "두 번째 세션 질문입니다"
    assert response.items[0].message_count == 1
    assert response.items[0].updated_at == datetime(2026, 5, 2, 10, 0, tzinfo=timezone.utc)
    assert response.items[1].title == "첫 질문"
    assert response.items[1].last_message_preview == "첫 세션 답변입니다"
    assert response.items[1].message_count == 2


def test_list_sessions_paginates_session_summaries() -> None:
    db = _make_session()
    first_session = ChatSession(title="오래된 세션")
    second_session = ChatSession(title="최신 세션")
    db.add_all([first_session, second_session])
    db.flush()
    db.add_all(
        [
            ChatMessage(
                session_id=first_session.id,
                role="user",
                content="오래된 질문",
                created_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
            ),
            ChatMessage(
                session_id=second_session.id,
                role="user",
                content="최신 질문",
                created_at=datetime(2026, 5, 2, 9, 0, tzinfo=timezone.utc),
            ),
        ]
    )
    db.commit()

    service = ChatService(
        agent=_make_agent(),
        repository=ChatRepository(db),
        dataset_repository=DatasetRepository(db),
    )

    response = service.list_sessions(skip=1, limit=1)

    assert response.total == 2
    assert len(response.items) == 1
    assert response.items[0].id == first_session.id


def test_invalid_source_id_does_not_create_empty_session() -> None:
    db = _make_session()
    service = ChatService(
        agent=_make_agent(),
        repository=ChatRepository(db),
        dataset_repository=DatasetRepository(db),
    )

    events = _collect_events(
        service.ask_stream(question="bad dataset question", source_id="missing-source")
    )

    assert [event["event"] for event in events] == ["error"]
    assert events[0]["data"]["error_code"] == "invalid_source_id"
    assert db.query(ChatSession).count() == 0
    assert db.query(ChatMessage).count() == 0
