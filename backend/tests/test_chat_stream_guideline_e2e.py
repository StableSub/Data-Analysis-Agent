from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.db import Base
from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.chat import models as _chat_models
from backend.app.modules.chat.dependencies import get_chat_service
from backend.app.modules.chat.repository import ChatRepository
from backend.app.modules.chat.router import router as chat_router
from backend.app.modules.chat.service import ChatService
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.datasets.repository import DatasetRepository
from backend.app.modules.datasets.service import DatasetReader
from backend.app.modules.profiling.service import (
    DatasetContextService,
    DatasetProfileService,
)
from backend.app.orchestration import builder
from backend.app.orchestration.builder import build_main_workflow
from backend.app.orchestration.client import AgentClient
from backend.app.orchestration.workflows import guideline as guideline_workflow
from backend.tests.guideline_first_fakes import (
    ActiveGuidelineService,
    FakeGuidelineRagService,
    GuidelineAwarePlannerLLM,
    GuidelineSummaryGateway,
    NoopRagService,
    guideline,
    guideline_chunk,
    planner_service,
)


class _WorkflowRuntime:
    def __init__(self, workflow: object) -> None:
        self.workflow = workflow

    async def __aenter__(self) -> object:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        _ = (exc_type, exc, traceback)
        return False


class _AnalysisService:
    def __init__(self, *, dataset_repository: DatasetRepository) -> None:
        self.dataset_repository = dataset_repository
        self.processor = AnalysisProcessor()
        self.planner_service = planner_service(GuidelineAwarePlannerLLM())
        reader = DatasetReader()
        profile_service = DatasetProfileService(
            repository=dataset_repository,
            reader=reader,
        )
        self.dataset_context_service = DatasetContextService(
            repository=dataset_repository,
            profile_service=profile_service,
            default_model="test-model",
        )
        self.planner_service.dataset_context_service = self.dataset_context_service

    def _get_dataset(self, source_id: str) -> Dataset | None:
        return self.dataset_repository.get_by_source_id(source_id)

    def _run_code_generation_loop(
        self,
        *,
        question: str,
        dataset: Dataset,
        analysis_plan: object,
        model_id: str | None,
    ) -> dict[str, object]:
        _ = (question, dataset, analysis_plan, model_id)
        return {
            "generated_code": "deterministic test code",
            "validated_code": "deterministic test code",
            "sandbox_result": {
                "ok": True,
                "stdout_json": {
                    "summary": "PART_NAME별 PassOrFail=1 불량률을 계산했습니다.",
                    "table": [
                        {"PART_NAME": "A", "defect_rate": 0.5},
                        {"PART_NAME": "B", "defect_rate": 0.5},
                    ],
                    "raw_metrics": {
                        "semantic_source": "guideline",
                        "defect_value": 1,
                    },
                    "used_columns": ["PART_NAME", "PassOrFail"],
                },
            },
            "analysis_result": {
                "execution_status": "success",
                "summary": "PART_NAME별 PassOrFail=1 불량률을 계산했습니다.",
                "table": [
                    {"PART_NAME": "A", "defect_rate": 0.5},
                    {"PART_NAME": "B", "defect_rate": 0.5},
                ],
                "raw_metrics": {
                    "semantic_source": "guideline",
                    "defect_value": 1,
                },
                "used_columns": ["PART_NAME", "PassOrFail"],
                "quality_status": "complete",
            },
            "retry_count": 0,
        }

    def _persist_result(
        self,
        *,
        question: str,
        source_id: str,
        session_id: object,
        analysis_plan: object,
        generated_code: object,
        execution_result: object,
    ) -> str:
        _ = (
            question,
            source_id,
            session_id,
            analysis_plan,
            generated_code,
            execution_result,
        )
        return "analysis-result-guideline-e2e"


class _VisualizationService:
    def build_from_analysis_result(
        self,
        *,
        source_id: str,
        analysis_plan: object,
        analysis_result: object,
    ) -> dict[str, object]:
        _ = (source_id, analysis_plan, analysis_result)
        return {
            "status": "generated",
            "summary": "PART_NAME별 불량률 막대그래프 데이터를 생성했습니다.",
            "artifact": {
                "chart_type": "bar",
                "x": "PART_NAME",
                "y": "defect_rate",
                "data": [
                    {"PART_NAME": "A", "defect_rate": 0.5},
                    {"PART_NAME": "B", "defect_rate": 0.5},
                ],
            },
        }


def _make_repositories() -> tuple[ChatRepository, DatasetRepository]:
    assert _chat_models.ChatSession.__tablename__ == "chat_sessions"
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    return ChatRepository(db), DatasetRepository(db)


def _register_dataset(
    repository: DatasetRepository,
    tmp_path: Path,
    *,
    source_id: str,
) -> None:
    csv_path = tmp_path / "quality.csv"
    csv_path.write_text(
        "PART_NO,PART_NAME,EQUIP_NAME,PassOrFail\n"
        "P1,A,E1,1\n"
        "P1,A,E1,0\n"
        "P2,B,E2,1\n"
        "P2,B,E2,0\n",
        encoding="utf-8",
    )
    repository.create(
        Dataset(
            source_id=source_id,
            filename="quality.csv",
            storage_path=str(csv_path),
            filesize=csv_path.stat().st_size,
        )
    )


def _parse_sse_events(raw_stream: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in raw_stream.strip().split("\n\n"):
        lines = block.splitlines()
        event_name = ""
        data = ""
        for line in lines:
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            if line.startswith("data: "):
                data = line.removeprefix("data: ")
        if event_name and data:
            events.append({"event": event_name, "data": json.loads(data)})
    return events


def _done_events(events: list[dict[str, object]]) -> Iterator[dict[str, Any]]:
    for event in events:
        if event.get("event") != "done":
            continue
        data = event.get("data")
        if isinstance(data, dict):
            yield cast(dict[str, Any], data)


def test_chat_stream_guideline_selected_dataset_uses_guideline_before_clarifying(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_id = "dataset-source"
    guideline_source_id = "guideline-source"
    chat_repository, dataset_repository = _make_repositories()
    _register_dataset(dataset_repository, tmp_path, source_id=source_id)

    analysis_service = _AnalysisService(dataset_repository=dataset_repository)
    main_planner = planner_service(GuidelineAwarePlannerLLM())
    main_planner.dataset_context_service = analysis_service.dataset_context_service

    monkeypatch.setattr(guideline_workflow, "LLMGateway", GuidelineSummaryGateway)
    monkeypatch.setattr(
        builder,
        "answer_data_question",
        lambda **_: "가이드라인 근거로 PART_NAME별 PassOrFail=1 불량률을 계산했습니다.",
    )

    workflow = build_main_workflow(
        planner_service=main_planner,
        analysis_service=analysis_service,
        preprocess_service=object(),
        eda_service=object(),
        rag_service=NoopRagService(),
        guideline_service=ActiveGuidelineService(
            active=guideline(guideline_source_id),
            guidelines={guideline_source_id: guideline(guideline_source_id)},
        ),
        guideline_rag_service=FakeGuidelineRagService(
            retrieved=[guideline_chunk(guideline_source_id)]
        ),
        visualization_service=_VisualizationService(),
        report_service=object(),
        default_model="test-model",
    )
    agent = AgentClient(
        workflow_runtime_factory=lambda: _WorkflowRuntime(workflow),
        default_model="test-model",
    )
    chat_service = ChatService(
        agent=agent,
        repository=chat_repository,
        dataset_repository=dataset_repository,
    )
    app = FastAPI()
    app.include_router(chat_router)
    app.dependency_overrides[get_chat_service] = lambda: chat_service
    client = TestClient(app)

    with client.stream(
        "POST",
        "/chats/stream",
        json={
            "question": "가이드라인 기준으로 제품별 불량률을 막대그래프로 시각화해줘.",
            "source_id": source_id,
            "guideline_source_id": guideline_source_id,
            "model_id": "test-model",
            "trace_id": "trace-guideline-e2e",
        },
    ) as response:
        raw_stream = response.read().decode("utf-8")

    assert response.status_code == 200
    events = _parse_sse_events(raw_stream)
    event_names = [event["event"] for event in events]
    assert event_names[0] == "session"
    assert "error" not in event_names, raw_stream
    assert "done" in event_names

    done = next(_done_events(events))
    assert done["status"] == "success"
    assert done["output_type"] == "data_qa"
    assert done["answer"].startswith("차트 데이터를 생성했습니다.")
    assert "PART_NAME별 불량률 막대그래프" in done["answer"]
    assert done["analysis_result"]["used_columns"] == ["PART_NAME", "PassOrFail"]
    assert done["visualization_result"]["status"] == "generated"
    assert done["evidence_package"]["guideline_status"] == "retrieved"
    assert done["evidence_package"]["guideline_retrieved_count"] == 1
    assert done["answer_quality"]["answerable"] is True
    assert done["output"]["answer_quality"]["answerable"] is True
    assert "clarification" not in json.dumps(done, ensure_ascii=False)
    assert done["output"]["type"] != "fast_common_analytics"
