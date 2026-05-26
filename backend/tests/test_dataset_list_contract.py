from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.db import Base
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.datasets.repository import DatasetRepository
from backend.app.modules.datasets.service import DatasetReader, DatasetService, DatasetStorage


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def test_list_datasets_excludes_missing_storage_files_by_default(tmp_path: Path) -> None:
    db = _make_session()
    existing_path = tmp_path / "valid.csv"
    existing_path.write_text("a,b\n1,2\n", encoding="utf-8")
    missing_path = tmp_path / "missing.csv"

    db.add_all(
        [
            Dataset(
                source_id="missing-source",
                filename="missing.csv",
                storage_path=str(missing_path),
                filesize=12,
            ),
            Dataset(
                source_id="valid-source",
                filename="valid.csv",
                storage_path=str(existing_path),
                filesize=8,
            ),
        ]
    )
    db.commit()

    service = DatasetService(
        repository=DatasetRepository(db),
        storage=DatasetStorage(tmp_path),
        reader=DatasetReader(),
    )

    items, total = service.list_datasets()

    assert total == 1
    assert [item.source_id for item in items] == ["valid-source"]


def test_list_datasets_paginates_after_filtering_missing_storage_files(tmp_path: Path) -> None:
    db = _make_session()
    first_path = tmp_path / "first.csv"
    second_path = tmp_path / "second.csv"
    first_path.write_text("a\n1\n", encoding="utf-8")
    second_path.write_text("a\n2\n", encoding="utf-8")

    db.add_all(
        [
            Dataset(
                source_id="missing-source",
                filename="missing.csv",
                storage_path=str(tmp_path / "missing.csv"),
                filesize=12,
            ),
            Dataset(
                source_id="first-source",
                filename="first.csv",
                storage_path=str(first_path),
                filesize=4,
            ),
            Dataset(
                source_id="second-source",
                filename="second.csv",
                storage_path=str(second_path),
                filesize=4,
            ),
        ]
    )
    db.commit()

    service = DatasetService(
        repository=DatasetRepository(db),
        storage=DatasetStorage(tmp_path),
        reader=DatasetReader(),
    )

    items, total = service.list_datasets(skip=1, limit=1)

    assert total == 2
    assert len(items) == 1
    assert items[0].source_id == "first-source"
