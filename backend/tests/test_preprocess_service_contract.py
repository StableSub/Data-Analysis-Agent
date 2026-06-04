from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.db import Base
from backend.app.modules.datasets.models import (
    DATASET_FILENAME_MAX_LENGTH,
    DATASET_SOURCE_ID_MAX_LENGTH,
    Dataset,
)
from backend.app.modules.datasets.repository import DatasetRepository
from backend.app.modules.datasets.service import DatasetReader
from backend.app.modules.preprocess.processor import PreprocessProcessor
from backend.app.modules.preprocess.schemas import ImputeOperation
from backend.app.modules.preprocess.service import PreprocessService
from backend.app.modules.preprocess.source_naming import PreprocessOutputTarget
from backend.app.modules.profiling.service import DatasetProfileService


def _make_repository() -> DatasetRepository:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return DatasetRepository(session_factory())


def _make_service(repository: DatasetRepository) -> PreprocessService:
    reader = DatasetReader()
    return PreprocessService(
        repository=repository,
        reader=reader,
        processor=PreprocessProcessor(),
        profile_service=DatasetProfileService(repository=repository, reader=reader),
    )


def _register_dataset(
    repository: DatasetRepository,
    path: Path,
    *,
    filename: str = "매출 데이터.csv",
) -> None:
    path.write_text("region,revenue\nnorth,100\nsouth,\nwest,300\n", encoding="utf-8")
    repository.create(
        Dataset(
            source_id="internal-source-id",
            filename=filename,
            storage_path=str(path),
            filesize=path.stat().st_size,
        )
    )


def test_apply_names_processed_dataset_from_visible_dataset_name(tmp_path: Path) -> None:
    repository = _make_repository()
    _register_dataset(repository, tmp_path / "storage_uuid_sales.csv")
    service = _make_service(repository)

    response = service.apply(
        source_id="internal-source-id",
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )

    output_dataset = repository.get_by_source_id(response.output_source_id)
    assert response.output_source_id == "매출_데이터_전처리_1"
    assert response.output_filename == "매출_데이터_전처리_1.csv"
    assert output_dataset is not None
    assert output_dataset.filename == "매출_데이터_전처리_1.csv"
    assert "internal-source-id" not in response.output_filename


def test_apply_increments_processed_dataset_name_sequence(tmp_path: Path) -> None:
    repository = _make_repository()
    _register_dataset(repository, tmp_path / "storage_uuid_sales.csv")
    service = _make_service(repository)

    first = service.apply(
        source_id="internal-source-id",
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )
    second = service.apply(
        source_id="internal-source-id",
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )

    assert first.output_filename == "매출_데이터_전처리_1.csv"
    assert second.output_filename == "매출_데이터_전처리_2.csv"


def test_apply_reuses_original_processed_name_base_when_input_is_processed(
    tmp_path: Path,
) -> None:
    repository = _make_repository()
    _register_dataset(repository, tmp_path / "storage_uuid_sales.csv")
    service = _make_service(repository)

    first = service.apply(
        source_id="internal-source-id",
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )
    second = service.apply(
        source_id=first.output_source_id,
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )

    assert first.output_filename == "매출_데이터_전처리_1.csv"
    assert second.output_filename == "매출_데이터_전처리_2.csv"


def test_apply_caps_named_source_id_to_dataset_contract(tmp_path: Path) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path / "storage_uuid_sales.csv",
        filename=f"{'품질데이터' * 80}.csv",
    )
    service = _make_service(repository)

    response = service.apply(
        source_id="internal-source-id",
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )

    assert len(response.output_source_id) <= DATASET_SOURCE_ID_MAX_LENGTH
    assert len(response.output_filename) <= DATASET_FILENAME_MAX_LENGTH
    assert len(response.output_filename.encode("utf-8")) <= DATASET_FILENAME_MAX_LENGTH
    assert response.output_source_id.endswith("_전처리_1")
    assert response.output_filename == f"{response.output_source_id}.csv"


def test_apply_retries_stale_named_source_id_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _make_repository()
    _register_dataset(repository, tmp_path / "storage_uuid_sales.csv")
    service = _make_service(repository)
    attempts = 0

    def stale_then_next_target(**_: object) -> PreprocessOutputTarget:
        nonlocal attempts
        attempts += 1
        suffix = 1 if attempts <= 2 else 2
        source_id = f"매출_데이터_전처리_{suffix}"
        return PreprocessOutputTarget(
            source_id=source_id,
            filename=f"{source_id}.csv",
            storage_path=tmp_path / f"{source_id}.csv",
        )

    monkeypatch.setattr(
        "backend.app.modules.preprocess.service.build_preprocess_output_target",
        stale_then_next_target,
    )

    first = service.apply(
        source_id="internal-source-id",
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )
    second = service.apply(
        source_id="internal-source-id",
        operations=[ImputeOperation(op="impute", columns=["revenue"], method="median")],
    )

    assert first.output_source_id == "매출_데이터_전처리_1"
    assert second.output_source_id == "매출_데이터_전처리_2"
    assert attempts == 3
    assert (tmp_path / "매출_데이터_전처리_1.csv").is_file()
    assert (tmp_path / "매출_데이터_전처리_2.csv").is_file()
