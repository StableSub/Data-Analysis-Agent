from __future__ import annotations

import builtins
from pathlib import Path
from typing import Any, cast

import pytest

from backend.app.modules.rag.dependencies import build_rag_service


class _Repository:
    def list_sources(self, source_filter: object = None) -> list[object]:
        _ = source_filter
        return []


class _DatasetRepository:
    pass


def test_build_rag_service_defers_embedding_model_import(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_import = builtins.__import__

    def guarded_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "backend.app.modules.rag.infra.embedding" or name == "sentence_transformers":
            raise AssertionError("embedding model should not load during service construction")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    service = build_rag_service(
        repository=cast(Any, _Repository()),
        dataset_repository=cast(Any, _DatasetRepository()),
        storage_dir=tmp_path,
    )

    assert service.embedder.model_name == "intfloat/multilingual-e5-small"
