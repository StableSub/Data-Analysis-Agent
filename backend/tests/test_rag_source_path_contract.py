from pathlib import Path

from backend.app.modules.datasets.models import DATASET_SOURCE_ID_MAX_LENGTH
from backend.app.modules.rag.models import RagChunk, RagSource
from backend.app.modules.rag.service import RagService


def _make_service(tmp_path: Path) -> RagService:
    service = object.__new__(RagService)
    service.storage_dir = tmp_path
    return service


def test_dataset_rag_source_columns_match_dataset_source_id_contract() -> None:
    assert RagSource.__table__.c.source_id.type.length == DATASET_SOURCE_ID_MAX_LENGTH
    assert RagChunk.__table__.c.source_id.type.length == DATASET_SOURCE_ID_MAX_LENGTH


def test_rag_uses_bounded_path_component_for_long_source_id(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    source_id = "a" * DATASET_SOURCE_ID_MAX_LENGTH

    source_component = service._source_dir(source_id).name
    temp_component = service._temp_dir(source_id).name
    backup_component = service._backup_dir(source_id).name

    assert source_component.startswith("source-")
    assert len(source_component.encode("utf-8")) <= 255
    assert len(temp_component.encode("utf-8")) <= 255
    assert len(backup_component.encode("utf-8")) <= 255


def test_rag_keeps_safe_source_id_as_path_component(tmp_path: Path) -> None:
    service = _make_service(tmp_path)
    source_id = "품질_데이터_전처리_1"

    assert service._source_dir(source_id).name == source_id
