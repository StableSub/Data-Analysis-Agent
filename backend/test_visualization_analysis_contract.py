from __future__ import annotations

import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from backend.app.modules.analysis.router import get_analysis_result
from backend.app.modules.results.repository import ResultsRepository
from backend.app.modules.visualization.router import create_visualization_from_analysis
from backend.app.modules.visualization.schemas import VisualizationFromAnalysisRequest


def _build_analysis_plan_json(analysis_type: str = "trend") -> dict[str, object]:
    return {
        "analysis_type": analysis_type,
        "objective": "Summarize sales trends",
        "required_columns": ["date", "sales"],
        "used_columns": ["date", "sales"],
        "filters": [],
        "group_by": [],
        "metrics": [],
        "derived_columns": [],
        "sort_by": [],
        "time_context": None,
        "expected_output": {
            "require_summary": True,
            "require_table": True,
            "require_raw_metrics": True,
            "expected_table_columns": [],
            "allow_empty_table": True,
            "minimum_rows": 0,
            "require_group_axis": False,
            "require_time_axis": False,
            "require_outlier_info": False,
        },
        "visualization_hint": {
            "preferred_chart": "line",
            "x": "date",
            "y": "sales",
            "series": None,
            "caption": None,
        },
        "empty_result_policy": "success_with_empty_summary",
        "metadata_snapshot": {
            "columns": ["date", "sales"],
            "dtypes": {"date": "datetime64[ns]", "sales": "int64"},
            "numeric_columns": ["sales"],
            "datetime_columns": ["date"],
            "categorical_columns": [],
            "row_count": 10,
            "timezone": None,
        },
        "codegen_strategy": "llm_codegen",
    }


class _FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0
        self.refreshes = 0

    def add(self, value) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, value) -> None:
        self.refreshes += 1


class _FakeResultsRepository:
    def __init__(self, result) -> None:
        self.result = result
        self.updated_chart_data = []

    def get_analysis_result(self, result_id: str):
        if result_id == self.result.id:
            return self.result
        return None

    def update_chart_data(self, result_id: str, chart_data):
        self.updated_chart_data.append((result_id, chart_data))
        return self.result

    def resolve_analysis_result_source_id(self, result) -> str | None:
        return ResultsRepository.resolve_analysis_result_source_id(result)

    def resolve_analysis_result_question(self, result) -> str:
        return ResultsRepository.resolve_analysis_result_question(result)

    def resolve_analysis_type(self, result) -> str:
        return ResultsRepository.resolve_analysis_type(result)


class _FakeVisualizationService:
    def __init__(self) -> None:
        self.calls = []

    def build_from_analysis_result(self, *, source_id: str, analysis_plan, analysis_result):
        self.calls.append(
            {
                "source_id": source_id,
                "analysis_plan": analysis_plan,
                "analysis_result": analysis_result,
            }
        )
        return {
            "status": "generated",
            "source_id": source_id,
            "summary": "line chart generated",
            "chart": {"chart_type": "line", "x": ["2026-01-01"], "series": [{"name": "sales", "y": [10]}]},
            "chart_data": {"chart_type": "line", "x": ["2026-01-01"], "series": [{"name": "sales", "y": [10]}]},
            "fallback_table": None,
        }


class ResultsRepositoryMetadataTests(unittest.TestCase):
    def test_create_analysis_result_persists_meta_into_result_json(self) -> None:
        repository = ResultsRepository(_FakeDb())

        result = repository.create_analysis_result(
            question="How did sales change?",
            source_id="dataset-1",
            session_id="7",
            analysis_plan=_build_analysis_plan_json(),
            generated_code="print('ok')",
            execution_result=SimpleNamespace(
                summary=None,
                raw_metrics={},
                table=[],
                used_columns=["date", "sales"],
                execution_status="success",
                error_stage=None,
                error_message=None,
            ),
        )

        self.assertIsInstance(result.result_json, dict)
        self.assertEqual(
            result.result_json["meta"],
            {
                "question": "How did sales change?",
                "source_id": "dataset-1",
                "session_id": "7",
            },
        )


class AnalysisResultRouteTests(unittest.TestCase):
    def test_get_analysis_result_includes_source_question_and_analysis_type(self) -> None:
        result = SimpleNamespace(
            id="analysis-1",
            analysis_plan_json=_build_analysis_plan_json("trend"),
            generated_code="print('ok')",
            used_columns=["date", "sales"],
            result_json={
                "summary": "Sales increased.",
                "raw_metrics": {"rows": 10},
                "meta": {
                    "source_id": "dataset-1",
                    "question": "How did sales change?",
                    "session_id": "7",
                },
            },
            table=[{"date": "2026-01-01", "sales": 10}],
            chart_data=None,
            execution_status="success",
            error_stage=None,
            error_message=None,
            created_at="2026-04-08T00:00:00Z",
            data_json=None,
        )
        repository = _FakeResultsRepository(result)

        payload = get_analysis_result("analysis-1", results_repository=repository)

        self.assertEqual(payload["source_id"], "dataset-1")
        self.assertEqual(payload["question"], "How did sales change?")
        self.assertEqual(payload["analysis_type"], "trend")
        self.assertEqual(payload["analysis_result_id"], "analysis-1")


class VisualizationFromAnalysisRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_route_uses_dataset_source_id_not_analysis_result_id(self) -> None:
        result = SimpleNamespace(
            id="analysis-1",
            analysis_plan_json=_build_analysis_plan_json("trend"),
            result_json={
                "summary": "Sales increased.",
                "raw_metrics": {"rows": 10},
                "meta": {
                    "source_id": "dataset-1",
                    "question": "How did sales change?",
                    "session_id": "7",
                },
            },
            table=[{"date": "2026-01-01", "sales": 10}],
            used_columns=["date", "sales"],
            execution_status="success",
            error_stage=None,
            error_message=None,
            chart_data=None,
            data_json=None,
        )
        repository = _FakeResultsRepository(result)
        service = _FakeVisualizationService()

        payload = await create_visualization_from_analysis(
            request=VisualizationFromAnalysisRequest(analysis_result_id="analysis-1"),
            service=service,
            results_repository=repository,
        )

        self.assertEqual(payload["source_id"], "dataset-1")
        self.assertEqual(service.calls[0]["source_id"], "dataset-1")
        self.assertNotEqual(payload["source_id"], "analysis-1")
        self.assertEqual(
            repository.updated_chart_data,
            [("analysis-1", payload["chart_data"])],
        )

    async def test_route_rejects_legacy_result_without_resolvable_source(self) -> None:
        result = SimpleNamespace(
            id="analysis-legacy",
            analysis_plan_json=_build_analysis_plan_json("trend"),
            result_json={"summary": "Sales increased.", "raw_metrics": {}},
            table=[],
            used_columns=["date", "sales"],
            execution_status="success",
            error_stage=None,
            error_message=None,
            chart_data=None,
            data_json=[],
        )
        repository = _FakeResultsRepository(result)
        service = _FakeVisualizationService()

        with self.assertRaises(HTTPException) as context:
            await create_visualization_from_analysis(
                request=VisualizationFromAnalysisRequest(analysis_result_id="analysis-legacy"),
                service=service,
                results_repository=repository,
            )

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(service.calls, [])
        self.assertEqual(repository.updated_chart_data, [])

    async def test_route_uses_legacy_data_json_source_id_fallback(self) -> None:
        result = SimpleNamespace(
            id="analysis-legacy",
            analysis_plan_json=_build_analysis_plan_json("trend"),
            result_json={"summary": "Sales increased.", "raw_metrics": {}},
            table=[{"date": "2026-01-01", "sales": 10}],
            used_columns=["date", "sales"],
            execution_status="success",
            error_stage=None,
            error_message=None,
            chart_data=None,
            data_json={
                "source_id": "dataset-legacy",
                "question": "Legacy question",
            },
        )
        repository = _FakeResultsRepository(result)
        service = _FakeVisualizationService()

        payload = await create_visualization_from_analysis(
            request=VisualizationFromAnalysisRequest(analysis_result_id="analysis-legacy"),
            service=service,
            results_repository=repository,
        )

        self.assertEqual(payload["source_id"], "dataset-legacy")
        self.assertEqual(service.calls[0]["source_id"], "dataset-legacy")


if __name__ == "__main__":
    unittest.main()
