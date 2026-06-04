from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.db import Base
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.datasets.repository import DatasetRepository
from backend.app.modules.datasets.service import DatasetReader
from backend.app.modules.preprocess.dependencies import get_preprocess_service
from backend.app.modules.preprocess.processor import PreprocessProcessor
from backend.app.modules.preprocess.router import router as preprocess_router
from backend.app.modules.preprocess.schemas import ImputeOperation
from backend.app.modules.preprocess.service import PreprocessService
from backend.app.modules.profiling.service import DatasetProfileService
from backend.app.modules.rag.service import RagService


def _make_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def _make_service(repository: DatasetRepository) -> PreprocessService:
    reader = DatasetReader()
    return PreprocessService(
        repository=repository,
        reader=reader,
        processor=PreprocessProcessor(),
        profile_service=DatasetProfileService(repository=repository, reader=reader),
    )


def _seed_dataset(
    *,
    db: Session,
    tmp_path: Path,
    source_id: str,
    filename: str,
    storage_name: str = "raw-storage-file.csv",
) -> Dataset:
    storage_path = tmp_path / storage_name
    storage_path.write_text("value,label\n1,A\n,B\n3,A\n", encoding="utf-8")
    dataset = Dataset(
        source_id=source_id,
        filename=filename,
        storage_path=str(storage_path),
        filesize=storage_path.stat().st_size,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def _impute_value_operation() -> ImputeOperation:
    return ImputeOperation(op="impute", columns=["value"], method="median")


def test_apply_names_preprocessed_source_from_dataset_filename(tmp_path: Path) -> None:
    db = _make_session()
    repository = DatasetRepository(db)
    _seed_dataset(
        db=db,
        tmp_path=tmp_path,
        source_id="raw-source",
        filename="품질 데이터.csv",
    )
    service = _make_service(repository)

    response = service.apply(
        source_id="raw-source",
        operations=[_impute_value_operation()],
    )

    assert response.output_source_id == "품질_데이터_전처리_1"
    assert response.output_filename == "품질_데이터_전처리_1.csv"
    assert response.output_source_id != response.input_source_id
    output_dataset = repository.get_by_source_id(response.output_source_id)
    assert output_dataset is not None
    assert str(output_dataset.filename) == "품질_데이터_전처리_1.csv"
    assert Path(str(output_dataset.storage_path)).name == "품질_데이터_전처리_1.csv"
    assert Path(str(output_dataset.storage_path)).is_file()


def test_apply_sanitizes_empty_like_names_and_increments_repeated_outputs(tmp_path: Path) -> None:
    db = _make_session()
    repository = DatasetRepository(db)
    _seed_dataset(
        db=db,
        tmp_path=tmp_path,
        source_id="raw-source",
        filename="!!!.csv",
    )
    service = _make_service(repository)

    first = service.apply(source_id="raw-source", operations=[_impute_value_operation()])
    second = service.apply(source_id="raw-source", operations=[_impute_value_operation()])

    assert first.output_source_id == "dataset_전처리_1"
    assert first.output_filename == "dataset_전처리_1.csv"
    assert second.output_source_id == "dataset_전처리_2"
    assert second.output_filename == "dataset_전처리_2.csv"
    assert repository.get_by_source_id("dataset_전처리_1") is not None
    assert repository.get_by_source_id("dataset_전처리_2") is not None


def test_rag_paths_accept_long_preprocess_source_id_without_shortening_public_id(
    tmp_path: Path,
) -> None:
    db = _make_session()
    repository = DatasetRepository(db)
    _seed_dataset(
        db=db,
        tmp_path=tmp_path,
        source_id="raw-source",
        filename=f"{'a' * 400}.csv",
    )
    service = _make_service(repository)

    response = service.apply(source_id="raw-source", operations=[_impute_value_operation()])

    assert len(response.output_source_id.encode("utf-8")) > 217
    rag_repository: Any = object()
    embedder: Any = type("FakeEmbedder", (), {"model_name": "fake", "embedding_dim": 1})()
    rag_service = RagService(
        repository=rag_repository,
        storage_dir=tmp_path / "rag",
        embedder=embedder,
    )

    paths = [
        rag_service._source_dir(response.output_source_id),
        rag_service._temp_dir(response.output_source_id),
        rag_service._backup_dir(response.output_source_id),
    ]
    assert paths[0].name != response.output_source_id
    for path in paths:
        assert all(len(part.encode("utf-8")) <= 255 for part in path.parts)
        path.mkdir(parents=True, exist_ok=True)


def test_preprocess_apply_route_accepts_existing_source_and_returns_named_output(
    tmp_path: Path,
) -> None:
    db = _make_session()
    repository = DatasetRepository(db)
    _seed_dataset(
        db=db,
        tmp_path=tmp_path,
        source_id="raw-source",
        filename="품질 데이터.csv",
    )
    service = _make_service(repository)
    app = FastAPI()
    app.dependency_overrides[get_preprocess_service] = lambda: service
    app.include_router(preprocess_router)
    client = TestClient(app)

    response = client.post(
        "/preprocess/apply",
        json={
            "source_id": "raw-source",
            "operations": [
                {"op": "impute", "columns": ["value"], "method": "median"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["input_source_id"] == "raw-source"
    assert payload["output_source_id"] == "품질_데이터_전처리_1"
    assert payload["output_filename"] == "품질_데이터_전처리_1.csv"
    assert payload["summary_diff"]["missing_total_delta"] == -1
