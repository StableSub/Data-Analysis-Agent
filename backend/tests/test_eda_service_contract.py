from pathlib import Path
import math
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.db import Base
from backend.app.modules.chat import models as _chat_models
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.datasets.repository import DatasetRepository
from backend.app.modules.datasets.service import DatasetReadError, DatasetReader
from backend.app.modules.eda import service as eda_service_module
from backend.app.modules.eda.dependencies import get_eda_service
from backend.app.modules.eda.router import router as eda_router
from backend.app.modules.eda.service import EDAService
from backend.app.modules.guidelines.dependencies import get_guideline_service
from backend.app.modules.profiling.service import DatasetProfileService


def _make_repository() -> DatasetRepository:
    assert _chat_models.ChatSession.__tablename__ == "chat_sessions"
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return DatasetRepository(session_factory())


def _make_eda_service(repository: DatasetRepository) -> EDAService:
    reader = DatasetReader()
    return EDAService(
        profile_service=DatasetProfileService(repository=repository, reader=reader),
        dataset_repository=repository,
        reader=reader,
    )


def _register_dataset(
    repository: DatasetRepository,
    tmp_path: Path,
    *,
    source_id: str,
    filename: str,
    content: str,
) -> None:
    csv_path = tmp_path / filename
    csv_path.write_text(content, encoding="utf-8")
    repository.create(
        Dataset(
            source_id=source_id,
            filename=filename,
            storage_path=str(csv_path),
            filesize=csv_path.stat().st_size,
        )
    )


def _make_eda_client(
    service: EDAService,
    *,
    guideline_service: object | None = None,
) -> TestClient:
    app = FastAPI()
    app.include_router(eda_router)
    app.dependency_overrides[get_eda_service] = lambda: service
    if guideline_service is not None:
        app.dependency_overrides[get_guideline_service] = lambda: guideline_service
    return TestClient(app, raise_server_exceptions=False)


def _finite_or_null(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, int | float) and math.isfinite(value)


def _assert_json_has_no_non_finite_numbers(value: object) -> None:
    if isinstance(value, float):
        assert math.isfinite(value)
        return
    if isinstance(value, list):
        for item in value:
            _assert_json_has_no_non_finite_numbers(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            _assert_json_has_no_non_finite_numbers(item)


def test_get_ai_summary_returns_deterministic_fallback_when_llm_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text(
        "region,revenue,orders\n"
        "north,100,10\n"
        "south,,12\n"
        "east,300,15\n",
        encoding="utf-8",
    )
    repository = _make_repository()
    repository.create(
        Dataset(
            source_id="eda-source",
            filename="sales.csv",
            storage_path=str(csv_path),
            filesize=csv_path.stat().st_size,
        )
    )
    service = _make_eda_service(repository)

    def raise_llm_error(**_: object) -> dict[str, object]:
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        eda_service_module,
        "generate_eda_ai_summary",
        raise_llm_error,
    )

    summary = service.get_ai_summary("eda-source")

    assert summary is not None
    assert summary.source_id == "eda-source"
    assert "3행" in summary.structure_summary
    assert summary.quality_issues
    assert summary.key_insights


def test_eda_insights_route_returns_fallback_when_llm_generation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text(
        "region,revenue,orders\n"
        "north,100,10\n"
        "south,,12\n"
        "east,300,15\n",
        encoding="utf-8",
    )
    repository = _make_repository()
    repository.create(
        Dataset(
            source_id="eda-source",
            filename="sales.csv",
            storage_path=str(csv_path),
            filesize=csv_path.stat().st_size,
        )
    )
    service = _make_eda_service(repository)

    def raise_llm_error(**_: object) -> dict[str, object]:
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(
        eda_service_module,
        "generate_eda_ai_summary",
        raise_llm_error,
    )
    app = FastAPI()
    app.include_router(eda_router)
    app.dependency_overrides[get_eda_service] = lambda: service
    client = TestClient(app)

    response = client.get("/eda/eda-source/insights")

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "eda-source"
    assert "3행" in body["structure_summary"]
    assert body["quality_issues"]
    assert body["key_insights"]
    assert "dataset_overview" not in body


def test_eda_insights_returns_dataset_aware_suggested_questions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="eda-source",
        filename="sales.csv",
        content=(
            "event_date,region,revenue,orders\n"
            "2026-01-01,north,100,10\n"
            "2026-01-02,south,,12\n"
            "2026-01-03,north,300,15\n"
            "2026-01-04,south,320,16\n"
        ),
    )

    def summarize(**_: object) -> dict[str, object]:
        return {
            "structure_summary": "4행 4열의 매출 데이터입니다.",
            "quality_issues": ["revenue 결측치를 먼저 확인하세요."],
            "key_insights": ["region별 revenue 차이를 확인할 수 있습니다."],
        }

    monkeypatch.setattr(
        eda_service_module,
        "generate_eda_ai_summary",
        summarize,
    )
    client = _make_eda_client(_make_eda_service(repository))

    response = client.get("/eda/eda-source/insights")

    assert response.status_code == 200
    suggested_questions = response.json()["suggested_questions"]
    assert len(suggested_questions) >= 4
    assert len(suggested_questions) <= 5
    assert {item["category"] for item in suggested_questions} >= {
        "quality",
        "comparison",
        "trend",
    }
    joined_questions = "\n".join(item["question"] for item in suggested_questions)
    assert "revenue" in joined_questions
    assert "region" in joined_questions
    assert "event_date" in joined_questions
    assert all(item["rationale"].strip() for item in suggested_questions)


def test_eda_insights_suggested_questions_skip_identifier_like_numeric_columns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="moldset-source",
        filename="moldset.csv",
        content=(
            "Unnamed: 0,PART_FACT_SERIAL,TimeStamp,PART_NAME,PassOrFail,Reason,Injection_Time\n"
            "1,1001,2026-01-01,A,0,,10.1\n"
            "2,1002,2026-01-02,A,1,gas,10.3\n"
            "3,1003,2026-01-03,B,0,,10.2\n"
            "4,1004,2026-01-04,B,1,scratch,10.8\n"
        ),
    )

    def summarize(**_: object) -> dict[str, object]:
        return {
            "structure_summary": "4행 7열의 품질 데이터입니다.",
            "quality_issues": ["Reason 결측치를 먼저 확인하세요."],
            "key_insights": ["PART_NAME별 PassOrFail 차이를 확인할 수 있습니다."],
        }

    monkeypatch.setattr(
        eda_service_module,
        "generate_eda_ai_summary",
        summarize,
    )
    client = _make_eda_client(_make_eda_service(repository))

    response = client.get("/eda/moldset-source/insights")

    assert response.status_code == 200
    joined_questions = "\n".join(
        item["question"] for item in response.json()["suggested_questions"]
    )
    assert "Unnamed" not in joined_questions
    assert "PART_FACT_SERIAL" not in joined_questions
    assert "PART_NAME" in joined_questions
    assert "PassOrFail" in joined_questions or "Injection_Time" in joined_questions


def test_eda_insights_adds_guideline_dataset_overview_when_guideline_is_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="moldset-source",
        filename="moldset_quality.csv",
        content=(
            "PART_NO,PART_NAME,PassOrFail,Defect_Code\n"
            "P-001,Bracket,1,\n"
            "P-002,Housing,0,SHORT\n"
            "P-001,Bracket,1,\n"
        ),
    )
    guideline_path = tmp_path / "moldset-guide.txt"
    guideline_path.write_text(
        "Moldset 품질 데이터는 제품별 금형 검사 결과를 기록한 데이터입니다.\n"
        "PART_NO는 제품 식별자, PART_NAME은 제품명, PassOrFail은 검사 판정 컬럼입니다.\n"
        "Defect_Code는 불량 원인을 담으며 제품별 불량률 계산에 함께 사용합니다.\n",
        encoding="utf-8",
    )
    guideline = SimpleNamespace(
        source_id="guideline-source",
        guideline_id="guide_moldset",
        filename="moldset-guide.pdf",
        storage_path=str(guideline_path),
    )

    class FakeGuidelineService:
        def get_guideline_by_source_id(self, source_id: str) -> Any:
            return guideline if source_id == guideline.source_id else None

    captured_payload: dict[str, Any] = {}

    def summarize(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        assert isinstance(payload, dict)
        captured_payload.update(payload)
        return {
            "structure_summary": "3행 4열의 금형 검사 데이터입니다.",
            "quality_issues": [],
            "key_insights": ["PassOrFail 판정과 Defect_Code를 함께 확인하세요."],
            "dataset_overview": {
                "summary": "제품별 금형 검사 결과를 담은 Moldset 품질 데이터입니다.",
                "key_points": [
                    "PART_NO는 제품 식별자입니다.",
                    "PassOrFail은 검사 판정 컬럼입니다.",
                ],
            },
        }

    monkeypatch.setattr(
        eda_service_module,
        "generate_eda_ai_summary",
        summarize,
    )

    client = _make_eda_client(
        _make_eda_service(repository),
        guideline_service=FakeGuidelineService(),
    )

    response = client.get(
        "/eda/moldset-source/insights",
        params={"guideline_source_id": "guideline-source"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "moldset-source"
    assert body["dataset_overview"]["guideline_source_id"] == "guideline-source"
    assert body["dataset_overview"]["guideline_filename"] == "moldset-guide.pdf"
    assert "제품별 금형 검사 결과" in body["dataset_overview"]["summary"]
    assert body["dataset_overview"]["key_points"]
    assert "guideline_context" in captured_payload
    assert "PART_NO" in str(captured_payload["guideline_context"])


def test_eda_insights_uses_active_guideline_when_no_guideline_is_selected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="moldset-source",
        filename="moldset_quality.csv",
        content=(
            "PART_NO,PART_NAME,PassOrFail\n"
            "P-001,Bracket,1\n"
            "P-002,Housing,0\n"
        ),
    )
    guideline_path = tmp_path / "active-moldset-guide.txt"
    guideline_path.write_text(
        "PART_NAME은 제품명이고 PassOrFail 컬럼에서 1은 불량입니다.\n",
        encoding="utf-8",
    )
    active_guideline = SimpleNamespace(
        source_id="active-guideline",
        guideline_id="guide_active",
        filename="active-guide.pdf",
        storage_path=str(guideline_path),
    )

    class FakeGuidelineService:
        def get_active_guideline(self) -> Any:
            return active_guideline

        def get_guideline_by_source_id(self, source_id: str) -> Any:
            return active_guideline if source_id == active_guideline.source_id else None

    captured_payload: dict[str, Any] = {}

    def summarize(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        assert isinstance(payload, dict)
        captured_payload.update(payload)
        return {
            "structure_summary": "2행 3열의 금형 검사 데이터입니다.",
            "quality_issues": [],
            "key_insights": ["PassOrFail 판정을 확인하세요."],
        }

    monkeypatch.setattr(
        eda_service_module,
        "generate_eda_ai_summary",
        summarize,
    )

    client = _make_eda_client(
        _make_eda_service(repository),
        guideline_service=FakeGuidelineService(),
    )

    response = client.get("/eda/moldset-source/insights")

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_overview"]["guideline_source_id"] == "active-guideline"
    assert body["dataset_overview"]["guideline_filename"] == "active-guide.pdf"
    assert "guideline_context" in captured_payload
    assert "PassOrFail" in str(captured_payload["guideline_context"])


def test_eda_routes_return_contract_for_valid_dataset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="eda-source",
        filename="metrics.csv",
        content=(
            "sample_id,value\n"
            "A001,10\n"
            "A002,20\n"
            "A003,30\n"
        ),
    )
    client = _make_eda_client(_make_eda_service(repository))

    def summarize(**_: object) -> dict[str, object]:
        return {
            "structure_summary": "3행 2열 데이터입니다.",
            "quality_issues": [],
            "key_insights": ["수치형 value 컬럼을 확인했습니다."],
        }

    monkeypatch.setattr(
        eda_service_module,
        "generate_eda_ai_summary",
        summarize,
    )

    endpoints = [
        "/eda/eda-source/profile",
        "/eda/eda-source/summary",
        "/eda/eda-source/quality",
        "/eda/eda-source/columns/types",
        "/eda/eda-source/stats",
        "/eda/eda-source/correlations/top",
        "/eda/eda-source/outliers",
        "/eda/eda-source/distribution?column=value",
        "/eda/eda-source/preprocess-recommendations",
        "/eda/eda-source/insights",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200, endpoint
        body = response.json()
        assert body["source_id"] == "eda-source"
        _assert_json_has_no_non_finite_numbers(body)


def test_dataset_reader_maps_usecols_mismatch_to_dataset_read_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "profile.csv"
    csv_path.write_text("present\n1\n2\n", encoding="utf-8")
    reader = DatasetReader()

    with pytest.raises(DatasetReadError):
        reader.read_csv(str(csv_path), usecols=["missing"])


def test_dataset_reader_chunk_iterator_maps_usecols_mismatch_to_dataset_read_error(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "profile.csv"
    csv_path.write_text("present\n1\n2\n", encoding="utf-8")
    reader = DatasetReader()

    with pytest.raises(DatasetReadError):
        list(reader.read_csv_chunks(str(csv_path), chunksize=1, usecols=["missing"]))


def test_numeric_eda_routes_return_finite_json_for_non_finite_values(
    tmp_path: Path,
) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="eda-source",
        filename="metrics.csv",
        content=(
            "value,other\n"
            "1,10\n"
            "inf,20\n"
            "3,30\n"
            "-inf,40\n"
            ",50\n"
        ),
    )
    client = _make_eda_client(_make_eda_service(repository))

    profile_response = client.get("/eda/eda-source/profile")
    assert profile_response.status_code == 200
    _assert_json_has_no_non_finite_numbers(profile_response.json())

    column_types_response = client.get("/eda/eda-source/columns/types")
    assert column_types_response.status_code == 200
    _assert_json_has_no_non_finite_numbers(column_types_response.json())

    stats_response = client.get("/eda/eda-source/stats")
    assert stats_response.status_code == 200
    stats_body = stats_response.json()
    value_stats = next(item for item in stats_body["columns"] if item["column"] == "value")
    assert value_stats["mean"] == 2.0
    assert value_stats["min"] == 1.0
    assert value_stats["max"] == 3.0
    for column_stats in stats_body["columns"]:
        for key in ("mean", "min", "max", "median", "std", "q1", "q3", "skew"):
            assert _finite_or_null(column_stats[key])

    distribution_response = client.get(
        "/eda/eda-source/distribution",
        params={"column": "value"},
    )
    assert distribution_response.status_code == 200
    distribution_body = distribution_response.json()
    assert distribution_body["total_count"] == 2
    for bin_item in distribution_body["bins"]:
        assert _finite_or_null(bin_item["lower"])
        assert _finite_or_null(bin_item["upper"])

    correlations_response = client.get("/eda/eda-source/correlations/top")
    assert correlations_response.status_code == 200
    for pair in correlations_response.json()["pairs"]:
        assert math.isfinite(pair["correlation"])

    outliers_response = client.get("/eda/eda-source/outliers")
    assert outliers_response.status_code == 200
    for column_outliers in outliers_response.json()["columns"]:
        for key in ("outlier_ratio", "q1", "q3", "iqr", "lower_bound", "upper_bound"):
            assert _finite_or_null(column_outliers[key])


@pytest.mark.parametrize(
    "endpoint",
    [
        "/eda/bad-source/profile",
        "/eda/bad-source/summary",
        "/eda/bad-source/quality",
        "/eda/bad-source/columns/types",
        "/eda/bad-source/stats",
        "/eda/bad-source/correlations/top",
        "/eda/bad-source/outliers",
        "/eda/bad-source/distribution?column=value",
        "/eda/bad-source/preprocess-recommendations",
        "/eda/bad-source/insights",
    ],
)
def test_eda_routes_map_unreadable_csv_to_422(
    tmp_path: Path,
    endpoint: str,
) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_bytes(b"\xff\xfe\x00\x00not-utf8")
    repository = _make_repository()
    repository.create(
        Dataset(
            source_id="bad-source",
            filename="bad.csv",
            storage_path=str(csv_path),
            filesize=csv_path.stat().st_size,
        )
    )
    client = _make_eda_client(_make_eda_service(repository))

    response = client.get(endpoint)

    assert response.status_code == 422
    assert response.json()["detail"]


@pytest.mark.parametrize(
    "endpoint",
    [
        "/eda/missing-source/profile",
        "/eda/missing-source/stats",
        "/eda/missing-source/distribution?column=value",
        "/eda/missing-source/insights",
    ],
)
def test_eda_routes_return_404_for_missing_storage_file(
    tmp_path: Path,
    endpoint: str,
) -> None:
    missing_path = tmp_path / "missing.csv"
    repository = _make_repository()
    repository.create(
        Dataset(
            source_id="missing-source",
            filename="missing.csv",
            storage_path=str(missing_path),
            filesize=0,
        )
    )
    client = _make_eda_client(_make_eda_service(repository))

    response = client.get(endpoint)

    assert response.status_code == 404
    assert response.json()["detail"]


def test_eda_distribution_error_status_codes(tmp_path: Path) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="eda-source",
        filename="metrics.csv",
        content=(
            "customer_id,value\n"
            "C001,10\n"
            "C002,20\n"
            "C003,30\n"
        ),
    )
    client = _make_eda_client(_make_eda_service(repository))

    unknown_response = client.get(
        "/eda/eda-source/distribution",
        params={"column": "missing"},
    )
    assert unknown_response.status_code == 400

    identifier_response = client.get(
        "/eda/eda-source/distribution",
        params={"column": "customer_id"},
    )
    assert identifier_response.status_code == 422


def test_no_numeric_dataset_returns_empty_numeric_eda_sections(tmp_path: Path) -> None:
    repository = _make_repository()
    _register_dataset(
        repository,
        tmp_path,
        source_id="eda-source",
        filename="segments.csv",
        content=(
            "segment,status\n"
            "north,open\n"
            "south,closed\n"
            "west,open\n"
        ),
    )
    client = _make_eda_client(_make_eda_service(repository))

    stats_response = client.get("/eda/eda-source/stats")
    assert stats_response.status_code == 200
    assert stats_response.json()["numeric_column_count"] == 0
    assert stats_response.json()["columns"] == []

    correlations_response = client.get("/eda/eda-source/correlations/top")
    assert correlations_response.status_code == 200
    assert correlations_response.json()["pairs"] == []

    outliers_response = client.get("/eda/eda-source/outliers")
    assert outliers_response.status_code == 200
    assert outliers_response.json()["numeric_column_count"] == 0
    assert outliers_response.json()["columns"] == []
