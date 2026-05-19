from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.db import Base
from backend.app.modules.chat import models as _chat_models
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.guidelines import models as _guideline_models
from backend.app.modules.rag import models as _rag_models
from backend.app.modules.reports import models as _report_models
from backend.app.modules.results import models as _result_models
from backend.app.modules.analysis.dependencies import (
    build_analysis_processor,
    build_analysis_run_service,
    build_analysis_sandbox,
    build_analysis_service,
    build_results_repository,
)
from backend.app.modules.datasets.dependencies import build_dataset_reader, build_dataset_repository
from backend.app.modules.eda.dependencies import build_eda_service
from backend.app.modules.guidelines.dependencies import build_guideline_repository, build_guideline_service
from backend.app.modules.planner.dependencies import build_planner_service
from backend.app.modules.preprocess.dependencies import build_preprocess_processor, build_preprocess_service
from backend.app.modules.profiling.dependencies import build_dataset_context_service, build_dataset_profile_service
from backend.app.modules.reports.dependencies import build_report_repository, build_report_service
from backend.app.modules.visualization.dependencies import build_visualization_service
from backend.app.orchestration.builder import build_main_workflow
from backend.app.orchestration.client import AgentClient
from eval_cases import RAW_DIR

_MODEL_IMPORTS = (
    _chat_models,
    _guideline_models,
    _rag_models,
    _report_models,
    _result_models,
)


@dataclass(frozen=True)
class LiveBenchmarkDataset:
    dataset_name: str
    source_id: str
    storage_path: Path
    filesize: int

    def as_agent_dataset(self) -> SimpleNamespace:
        return SimpleNamespace(source_id=self.source_id)


DATASET_SOURCE_ENV = {
    "moldset_labeled.csv": "BENCHMARK_SOURCE_ID_MOLDSET_LABELED",
    "unlabeled_data.csv": "BENCHMARK_SOURCE_ID_UNLABELED",
    "moldset_labeled_cn7.csv": "BENCHMARK_SOURCE_ID_MOLDSET_LABELED_CN7",
    "moldset_labeled_rg3.csv": "BENCHMARK_SOURCE_ID_MOLDSET_LABELED_RG3",
    "labeled_data.csv": "BENCHMARK_SOURCE_ID_LABELED_DATA",
}

DATASET_PATH_ENV = {
    "moldset_labeled.csv": "BENCHMARK_RAW_PATH_MOLDSET_LABELED",
    "unlabeled_data.csv": "BENCHMARK_RAW_PATH_UNLABELED",
    "moldset_labeled_cn7.csv": "BENCHMARK_RAW_PATH_MOLDSET_LABELED_CN7",
    "moldset_labeled_rg3.csv": "BENCHMARK_RAW_PATH_MOLDSET_LABELED_RG3",
    "labeled_data.csv": "BENCHMARK_RAW_PATH_LABELED_DATA",
}

DEFAULT_LIVE_CASE_IDS = ("p0_moldset_label_distribution",)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_dotenv_if_present() -> None:
    env_path = _repo_root() / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(line)
        if parsed is None:
            continue
        key, value = parsed
        os.environ.setdefault(key, value)


load_dotenv_if_present()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live_benchmark: opt-in benchmark tests that may call external LLM/workflow services",
    )


def live_benchmark_enabled() -> bool:
    return os.environ.get("RUN_LIVE_BENCHMARK") == "1"


def require_live_benchmark() -> None:
    if not live_benchmark_enabled():
        pytest.skip("set RUN_LIVE_BENCHMARK=1 in .env or environment to run opt-in live benchmark tests")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live LLM workflow benchmark runs")
    if importlib.util.find_spec("langchain_openai") is None:
        pytest.skip("langchain-openai is required for live LLM workflow benchmark runs")


def selected_live_case_ids() -> tuple[str, ...]:
    raw_value = os.environ.get("BENCHMARK_LIVE_CASE_IDS", "")
    selected = tuple(case_id.strip() for case_id in raw_value.split(",") if case_id.strip())
    return selected or DEFAULT_LIVE_CASE_IDS


def live_model_id() -> str | None:
    return os.environ.get("BENCHMARK_MODEL_ID") or None


def live_timeout_seconds() -> float:
    raw_value = os.environ.get("BENCHMARK_LIVE_TIMEOUT_SECONDS", "120")
    return float(raw_value)


def _storage_path_for(dataset_name: str) -> Path:
    override_key = DATASET_PATH_ENV[dataset_name]
    override_value = os.environ.get(override_key)
    if override_value:
        return Path(override_value).expanduser().resolve()
    return RAW_DIR / dataset_name


def _source_id_for(dataset_name: str) -> str:
    source_env = DATASET_SOURCE_ENV[dataset_name]
    source_id = os.environ.get(source_env, "").strip()
    if source_id:
        return source_id
    stem = Path(dataset_name).stem.replace("_", "-")
    return f"benchmark-{stem}"[:36]


def benchmark_dataset_registry() -> dict[str, LiveBenchmarkDataset]:
    registry: dict[str, LiveBenchmarkDataset] = {}
    for dataset_name in DATASET_SOURCE_ENV:
        storage_path = _storage_path_for(dataset_name)
        if not storage_path.exists():
            continue
        registry[dataset_name] = LiveBenchmarkDataset(
            dataset_name=dataset_name,
            source_id=_source_id_for(dataset_name),
            storage_path=storage_path,
            filesize=storage_path.stat().st_size,
        )
    return registry


def require_benchmark_dataset(dataset_name: str) -> LiveBenchmarkDataset:
    require_live_benchmark()
    if dataset_name not in DATASET_SOURCE_ENV:
        pytest.skip(f"no live benchmark dataset mapping is registered for {dataset_name}")
    storage_path = _storage_path_for(dataset_name)
    if not storage_path.exists():
        pytest.skip(f"live benchmark raw dataset is missing: {storage_path}")
    return LiveBenchmarkDataset(
        dataset_name=dataset_name,
        source_id=_source_id_for(dataset_name),
        storage_path=storage_path,
        filesize=storage_path.stat().st_size,
    )


def selected_cases(cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    selected_ids = set(selected_live_case_ids())
    return [case for case in cases if str(case.get("case_id")) in selected_ids]


@pytest.fixture
def live_benchmark_session(tmp_path: Path):
    require_live_benchmark()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'live-benchmark.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        for registration in benchmark_dataset_registry().values():
            session.add(
                Dataset(
                    source_id=registration.source_id,
                    filename=registration.dataset_name,
                    storage_path=str(registration.storage_path),
                    filesize=registration.filesize,
                )
            )
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()



class _NoopRagService:
    def ensure_index_for_source(self, source_id: str) -> dict[str, str]:
        return {"status": "unsupported_format", "source_id": source_id}

    def query_for_source(self, *, query: str, top_k: int, source_id: str) -> list[Any]:
        return []

    def build_context(self, retrieved: list[Any]) -> str:
        return ""


class _NoopGuidelineRagService:
    def ensure_index_for_guideline(self, guideline: Any) -> dict[str, str]:
        return {"status": "no_active_guideline"}

    def query_for_source(self, *, query: str, source_id: str, top_k: int) -> list[Any]:
        return []

    def build_context(self, retrieved: list[Any]) -> str:
        return ""


def _build_live_agent_client(*, db: Any, checkpoint_db_path: Path) -> AgentClient:
    agent_box: dict[str, AgentClient] = {}

    @asynccontextmanager
    async def workflow_runtime_factory():
        agent = agent_box["agent"]
        dataset_repository = build_dataset_repository(db)
        dataset_reader = build_dataset_reader()
        profile_service = build_dataset_profile_service(
            repository=dataset_repository,
            reader=dataset_reader,
        )
        dataset_context_service = build_dataset_context_service(
            repository=dataset_repository,
            profile_service=profile_service,
        )
        planner_service = build_planner_service(
            dataset_context_service=dataset_context_service,
        )
        eda_service = build_eda_service(
            profile_service=profile_service,
            dataset_repository=dataset_repository,
            reader=dataset_reader,
        )
        visualization_service = build_visualization_service(
            repository=dataset_repository,
            reader=dataset_reader,
        )
        analysis_service = build_analysis_service(
            repository=dataset_repository,
            dataset_context_service=dataset_context_service,
            planner_service=planner_service,
            processor=build_analysis_processor(),
            run_service=build_analysis_run_service(),
            sandbox=build_analysis_sandbox(),
            results_repository=build_results_repository(db=db),
            visualization_service=visualization_service,
        )
        preprocess_service = build_preprocess_service(
            repository=dataset_repository,
            reader=dataset_reader,
            processor=build_preprocess_processor(),
            profile_service=profile_service,
        )
        guideline_service = build_guideline_service(
            repository=build_guideline_repository(db),
        )
        report_service = build_report_service(
            repository=build_report_repository(db),
        )
        async with AsyncSqliteSaver.from_conn_string(str(checkpoint_db_path)) as checkpointer:
            workflow = build_main_workflow(
                planner_service=planner_service,
                analysis_service=analysis_service,
                preprocess_service=preprocess_service,
                eda_service=eda_service,
                rag_service=_NoopRagService(),
                guideline_service=guideline_service,
                guideline_rag_service=_NoopGuidelineRagService(),
                visualization_service=visualization_service,
                report_service=report_service,
                default_model=agent.default_model,
                checkpointer=checkpointer,
            )
            yield workflow

    agent = AgentClient(workflow_runtime_factory=workflow_runtime_factory)
    agent_box["agent"] = agent
    return agent


@pytest.fixture
def live_agent_client(live_benchmark_session, tmp_path: Path):
    return _build_live_agent_client(
        db=live_benchmark_session,
        checkpoint_db_path=tmp_path / "live-langgraph-checkpoints.db",
    )
