from __future__ import annotations

import unittest
from types import SimpleNamespace

from backend.app.modules.analysis.schemas import (
    AnalysisExecutionResult,
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    VisualizationHint,
)
from backend.app.modules.preprocess.executor import execute_preprocess_plan
from backend.app.modules.preprocess.schemas import PreprocessApplyResponse
from backend.app.modules.planner.schemas import PlanningResult
from backend.app.orchestration.utils import resolve_target_source_id
from backend.app.orchestration.workflows.analysis import build_analysis_workflow


class _FakeProcessor:
    def build_error(self, stage: str, message: str, detail: dict | None = None):
        return SimpleNamespace(
            stage=stage,
            message=message,
            detail=detail or {},
            model_dump=lambda: {
                "stage": stage,
                "message": message,
                "detail": detail or {},
            },
        )


class _FakeDatasetContext:
    def __init__(self, source_id: str) -> None:
        self._payload = {
            "source_id": source_id,
            "filename": f"{source_id}.csv",
            "available": True,
            "row_count_total": 3,
            "row_count_sample": 3,
            "column_count": 2,
            "columns": ["Age", "Cabin"],
            "dtypes": {"Age": "float64", "Cabin": "object"},
            "logical_types": {"Age": "numerical", "Cabin": "categorical"},
            "type_columns": {"numerical": ["Age"], "categorical": ["Cabin"]},
            "numeric_columns": ["Age"],
            "datetime_columns": [],
            "categorical_columns": ["Cabin"],
            "boolean_columns": [],
            "identifier_columns": [],
            "group_key_columns": [],
            "sample_rows": [],
            "missing_rates": {"Age": 0.199, "Cabin": 0.771},
            "quality_summary": {},
        }

    def model_dump(self) -> dict:
        return dict(self._payload)


class _FakeDatasetContextService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def build_context(self, source_id: str) -> _FakeDatasetContext:
        self.calls.append(source_id)
        return _FakeDatasetContext(source_id)


class _FakePlannerService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def plan(
        self,
        *,
        user_input: str,
        request_context: str,
        source_id: str,
        dataset_context: dict,
        guideline_context: dict | None,
        model_id: str | None,
    ) -> PlanningResult:
        self.calls.append(source_id)
        metadata = MetadataSnapshot(
            columns=["Age", "Cabin"],
            dtypes={"Age": "float64", "Cabin": "object"},
            numeric_columns=["Age"],
            categorical_columns=["Cabin"],
            datetime_columns=[],
            row_count=3,
        )
        return PlanningResult(
            route="analysis",
            analysis_plan=AnalysisPlan(
                analysis_type="missing_values_analysis",
                objective="결측치를 요약한다.",
                required_columns=["Age", "Cabin"],
                used_columns=["Age", "Cabin"],
                filters=[],
                group_by=[],
                metrics=[],
                derived_columns=[],
                sort_by=[],
                time_context=None,
                expected_output=ExpectedOutputSpec(),
                visualization_hint=VisualizationHint(preferred_chart="none"),
                empty_result_policy="success_with_empty_summary",
                metadata_snapshot=metadata,
                codegen_strategy="llm_codegen",
            ),
        )


class _FakeAnalysisService:
    def __init__(self) -> None:
        self.dataset_context_service = _FakeDatasetContextService()
        self.planner_service = _FakePlannerService()
        self.processor = _FakeProcessor()
        self.persist_calls: list[str] = []
        self.dataset_fetch_calls: list[str] = []

    def _get_dataset(self, source_id: str):
        self.dataset_fetch_calls.append(source_id)
        return SimpleNamespace(source_id=source_id, storage_path=f"/tmp/{source_id}.csv")

    def _run_code_generation_loop(
        self,
        *,
        question: str,
        dataset,
        analysis_plan: dict,
        model_id: str | None,
    ) -> dict:
        return {
            "generated_code": "print('ok')",
            "validated_code": "print('ok')",
            "sandbox_result": {"ok": True},
            "analysis_result": AnalysisExecutionResult(
                execution_status="success",
                summary=f"dataset={dataset.source_id}",
                used_columns=["Age", "Cabin"],
            ).model_dump(),
            "analysis_error": None,
            "retry_count": 0,
        }

    def _persist_result(
        self,
        *,
        question: str,
        source_id: str,
        session_id: str | None,
        analysis_plan: dict,
        generated_code: str,
        execution_result: AnalysisExecutionResult,
    ) -> str:
        self.persist_calls.append(source_id)
        return "result-1"


class _FakePreprocessService:
    def apply(self, source_id: str, operations):
        return PreprocessApplyResponse(
            input_source_id=source_id,
            output_source_id="processed-source",
            output_filename="processed-source.csv",
        )


class SourceSelectionTests(unittest.TestCase):
    def test_resolve_target_source_id_prefers_applied_output_source(self) -> None:
        state = {
            "source_id": "raw-source",
            "preprocess_result": {
                "status": "applied",
                "input_source_id": "raw-source",
                "output_source_id": "processed-source",
            },
            "rag_result": {"source_id": "rag-source"},
        }

        self.assertEqual(resolve_target_source_id(state), "processed-source")

    def test_execute_preprocess_plan_promotes_output_source_to_active_source(self) -> None:
        result = execute_preprocess_plan(
            source_id="raw-source",
            preprocess_plan={
                "operations": [
                    {
                        "op": "impute",
                        "columns": ["Age"],
                        "method": "mean",
                    }
                ]
            },
            approved_plan=None,
            dataset_profile=None,
            preprocess_service=_FakePreprocessService(),
        )

        self.assertEqual(result["source_id"], "processed-source")
        self.assertEqual(result["preprocess_result"]["input_source_id"], "raw-source")
        self.assertEqual(result["preprocess_result"]["output_source_id"], "processed-source")

    def test_analysis_workflow_uses_processed_source_after_preprocess(self) -> None:
        analysis_service = _FakeAnalysisService()
        workflow = build_analysis_workflow(analysis_service=analysis_service)

        result = workflow.invoke(
            {
                "user_input": "결측치 현황을 알려줘",
                "source_id": "raw-source",
                "session_id": "session-1",
                "preprocess_result": {
                    "status": "applied",
                    "input_source_id": "raw-source",
                    "output_source_id": "processed-source",
                },
            }
        )

        self.assertEqual(result["final_status"], "success")
        self.assertEqual(result["dataset_context"]["source_id"], "processed-source")
        self.assertEqual(analysis_service.planner_service.calls, ["processed-source"])
        self.assertEqual(analysis_service.dataset_fetch_calls, ["processed-source"])
        self.assertEqual(analysis_service.persist_calls, ["processed-source"])


if __name__ == "__main__":
    unittest.main()
