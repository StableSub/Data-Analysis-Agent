from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pandas as pd

from backend.app.modules.profiling.service import (
    DatasetContextService,
    DatasetProfileService,
)


class _FakeRepository:
    def __init__(self, storage_path: Path, *, source_id: str = "dataset-source") -> None:
        self._storage_path = storage_path
        self._source_id = source_id

    def get_by_source_id(self, source_id: str) -> SimpleNamespace | None:
        if source_id != self._source_id:
            return None
        return SimpleNamespace(
            source_id=source_id,
            storage_path=str(self._storage_path),
            filename="labels.csv",
        )


class _FakeReader:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def read_csv(self, storage_path: str, **_: object) -> pd.DataFrame:
        return self._df.copy()

    def read_csv_chunks(self, storage_path: str, **_: object) -> list[pd.DataFrame]:
        return [self._df.copy()]


def _build_context_service(
    tmp_path: Path,
    *,
    source_id: str = "dataset-source",
) -> DatasetContextService:
    storage_path = tmp_path / f"{source_id}.csv"
    storage_path.write_text("PART_NAME,PassOrFail\nA,0\nB,1\n", encoding="utf-8")
    df = pd.DataFrame(
        {
            "PART_NAME": ["A", "B"],
            "PassOrFail": [0, 1],
        }
    )
    repository = _FakeRepository(storage_path, source_id=source_id)
    profile_service = DatasetProfileService(
        repository=cast(Any, repository),
        reader=cast(Any, _FakeReader(df)),
    )
    return DatasetContextService(
        repository=cast(Any, repository),
        profile_service=profile_service,
    )


def test_dataset_context_does_not_call_ai_aliases_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = _build_context_service(tmp_path)

    def fail_generate_column_aliases(**_: object) -> dict[str, list[str]]:
        raise AssertionError("AI column aliases must be opt-in")

    monkeypatch.setattr(
        "backend.app.modules.profiling.service.generate_column_aliases",
        fail_generate_column_aliases,
    )

    context = service.build_context("dataset-source")

    assert context.available is True
    assert context.column_aliases["PART_NAME"] == ["PART NAME", "PARTNAME"]
    assert context.column_aliases["PassOrFail"] == ["Pass Or Fail"]


def test_dataset_context_can_opt_in_to_ai_aliases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = _build_context_service(tmp_path, source_id="dataset-source-ai")

    def generate_column_aliases(**_: object) -> dict[str, list[str]]:
        return {"PART_NAME": ["제품명"]}

    monkeypatch.setattr(
        "backend.app.modules.profiling.service.generate_column_aliases",
        generate_column_aliases,
    )

    context = service.build_context("dataset-source-ai", include_ai_aliases=True)

    assert context.column_aliases["PART_NAME"] == ["PART NAME", "PARTNAME", "제품명"]
