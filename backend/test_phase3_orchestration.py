import unittest
from unittest.mock import patch

from backend.app.modules.analysis.schemas import (
    AnalysisError,
    AnalysisExecutionResult,
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    MetricSpec,
    VisualizationHint,
)
from backend.app.modules.planner.schemas import PlanningResult
from backend.app.modules.profiling.schemas import DatasetContext
from backend.app.orchestration.builder import build_main_workflow
from backend.app.orchestration.intake_router import build_intake_router_workflow
from backend.app.orchestration.workflows.analysis import build_analysis_workflow


def _make_dataset_context(source_id: str) -> DatasetContext:
    if source_id == "dataset-2":
        columns = ["region", "clean_sales"]
        numeric_columns = ["clean_sales"]
    else:
        columns = ["region", "sales"]
        numeric_columns = ["sales"]
    return DatasetContext(
        source_id=source_id,
        filename=f"{source_id}.csv",
        available=True,
        row_count_total=120,
        row_count_sample=3,
        column_count=len(columns),
        columns=columns,
        dtypes={column: "int64" if column in numeric_columns else "object" for column in columns},
        logical_types={
            column: ("numerical" if column in numeric_columns else "categorical")
            for column in columns
        },
        type_columns={
            "numerical": numeric_columns,
            "categorical": [column for column in columns if column not in numeric_columns],
            "datetime": [],
            "boolean": [],
            "identifier": [],
            "group_key": [],
        },
        numeric_columns=numeric_columns,
        datetime_columns=[],
        categorical_columns=[column for column in columns if column not in numeric_columns],
        boolean_columns=[],
        identifier_columns=[],
        group_key_columns=[],
        sample_rows=[],
        missing_rates={},
    )


def _make_analysis_plan(source_id: str) -> AnalysisPlan:
    dataset_context = _make_dataset_context(source_id)
    metric_column = dataset_context.numeric_columns[0]
    return AnalysisPlan(
        analysis_type="aggregation",
        objective=f"{metric_column} 합계",
        required_columns=[metric_column],
        used_columns=[metric_column],
        filters=[],
        group_by=[],
        metrics=[
            MetricSpec(
                name=metric_column,
                aggregation="sum",
                column=metric_column,
                alias=f"total_{metric_column}",
            )
        ],
        derived_columns=[],
        sort_by=[],
        time_context=None,
        expected_output=ExpectedOutputSpec(),
        visualization_hint=VisualizationHint(),
        empty_result_policy="success_with_empty_table",
        metadata_snapshot=MetadataSnapshot(
            columns=dataset_context.columns,
            dtypes=dataset_context.dtypes,
            numeric_columns=dataset_context.numeric_columns,
            datetime_columns=dataset_context.datetime_columns,
            categorical_columns=dataset_context.categorical_columns,
            row_count=dataset_context.row_count_total,
        ),
        codegen_strategy="llm_codegen",
    )


class _DatasetContextServiceStub:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def build_context(self, source_id: str) -> DatasetContext:
        self.calls.append(source_id)
        return _make_dataset_context(source_id)


class _PlannerServiceStub:
    def __init__(self, *, route: str = "analysis") -> None:
        self.route = route
        self.plan_calls: list[dict] = []
        self.dataset_context_service = _DatasetContextServiceStub()

    def plan(self, **kwargs) -> PlanningResult:
        self.plan_calls.append(kwargs)
        source_id = str(kwargs.get("source_id") or "")
        if self.route == "fallback_rag":
            return PlanningResult(route="fallback_rag")
        return PlanningResult(
            route="analysis",
            preprocess_required=False,
            analysis_plan=_make_analysis_plan(source_id),
        )


class _ProcessorStub:
    def build_error(self, stage: str, message: str, detail=None) -> AnalysisError:
        return AnalysisError(stage=stage, message=message, detail=detail or {})


class _AnalysisServiceStub:
    def __init__(self, planner_service: _PlannerServiceStub) -> None:
        self.planner_service = planner_service
        self.dataset_context_service = planner_service.dataset_context_service
        self.processor = _ProcessorStub()
        self.datasets_requested: list[str] = []
        self.execution_calls: list[dict] = []
        self.persist_calls: list[str] = []

    def _get_dataset(self, source_id: str):
        self.datasets_requested.append(source_id)
        return {"source_id": source_id}

    def _run_code_generation_loop(self, *, question: str, dataset, analysis_plan, model_id):
        plan_dict = analysis_plan if isinstance(analysis_plan, dict) else analysis_plan.model_dump()
        used_columns = list(plan_dict.get("used_columns") or [])
        self.execution_calls.append(
            {
                "question": question,
                "dataset": dataset,
                "analysis_plan": plan_dict,
            }
        )
        return {
            "generated_code": "print('ok')",
            "validated_code": "print('ok')",
            "sandbox_result": {"ok": True},
            "analysis_result": AnalysisExecutionResult(
                execution_status="success",
                summary=f"{used_columns[0]} analysis complete",
                table=[{used_columns[0]: 1}] if used_columns else [],
                raw_metrics={"value": 1},
                used_columns=used_columns,
            ).model_dump(),
            "analysis_error": None,
            "final_status": "success",
            "retry_count": 0,
        }

    def _persist_result(
        self,
        *,
        question: str,
        source_id: str,
        session_id,
        analysis_plan,
        generated_code,
        execution_result,
    ) -> str:
        self.persist_calls.append(source_id)
        return f"result-{source_id}"


class _GuidelineServiceStub:
    def get_active_guideline(self):
        return None

    def get_guideline_by_source_id(self, source_id: str):
        return None


class _GuidelineRagServiceStub:
    def ensure_index_for_guideline(self, guideline):
        return {"status": "existing"}

    def query_for_source(self, **kwargs):
        return []

    def build_context(self, retrieved):
        return ""


class _RagServiceStub:
    def __init__(self) -> None:
        self.ensure_calls: list[str] = []

    def ensure_index_for_source(self, source_id: str):
        self.ensure_calls.append(source_id)
        return {"status": "existing"}

    def query_for_source(self, **kwargs):
        return []

    def build_context(self, retrieved):
        return ""


class _UnusedStub:
    pass


class Phase3OrchestrationTests(unittest.TestCase):
    def test_intake_routes_dataset_selected_without_calling_planner(self) -> None:
        planner_service = _PlannerServiceStub()
        workflow = build_intake_router_workflow(planner_service=planner_service)

        result = workflow.invoke({"user_input": "매출 합계", "source_id": "dataset-1"})

        self.assertEqual(result["handoff"]["next_step"], "dataset_selected")
        self.assertEqual(planner_service.plan_calls, [])

    def test_main_workflow_defaults_dataset_selected_path_to_analysis(self) -> None:
        planner_service = _PlannerServiceStub(route="analysis")
        analysis_service = _AnalysisServiceStub(planner_service)
        rag_service = _RagServiceStub()
        workflow = build_main_workflow(
            planner_service=planner_service,
            analysis_service=analysis_service,
            preprocess_service=_UnusedStub(),
            eda_service=_UnusedStub(),
            rag_service=rag_service,
            guideline_service=_GuidelineServiceStub(),
            guideline_rag_service=_GuidelineRagServiceStub(),
            visualization_service=_UnusedStub(),
            report_service=_UnusedStub(),
        )

        with patch("backend.app.orchestration.builder.answer_data_question", return_value="final answer"):
            result = workflow.invoke({"user_input": "매출 합계", "source_id": "dataset-1"})

        self.assertEqual(len(planner_service.plan_calls), 1)
        self.assertEqual(planner_service.plan_calls[0]["guideline_context"]["status"], "no_active_guideline")
        self.assertEqual(result["planning_result"]["route"], "analysis")
        self.assertEqual(result["merged_context"]["dataset_context"]["source_id"], "dataset-1")
        self.assertEqual(result["merged_context"]["guideline_context"]["status"], "no_active_guideline")
        self.assertEqual(analysis_service.datasets_requested, ["dataset-1"])
        self.assertEqual(rag_service.ensure_calls, [])
        self.assertEqual(result["output"]["type"], "data_qa")

    def test_main_workflow_uses_rag_only_for_fallback_route(self) -> None:
        planner_service = _PlannerServiceStub(route="fallback_rag")
        analysis_service = _AnalysisServiceStub(planner_service)
        rag_service = _RagServiceStub()
        workflow = build_main_workflow(
            planner_service=planner_service,
            analysis_service=analysis_service,
            preprocess_service=_UnusedStub(),
            eda_service=_UnusedStub(),
            rag_service=rag_service,
            guideline_service=_GuidelineServiceStub(),
            guideline_rag_service=_GuidelineRagServiceStub(),
            visualization_service=_UnusedStub(),
            report_service=_UnusedStub(),
        )

        with patch("backend.app.orchestration.builder.answer_data_question", return_value="rag answer"):
            result = workflow.invoke({"user_input": "파일 설명해줘", "source_id": "dataset-1"})

        self.assertEqual(len(planner_service.plan_calls), 1)
        self.assertEqual(result["planning_result"]["route"], "fallback_rag")
        self.assertEqual(rag_service.ensure_calls, ["dataset-1"])
        self.assertEqual(analysis_service.datasets_requested, [])
        self.assertEqual(result["output"]["type"], "data_qa")

    def test_analysis_workflow_replans_when_preprocess_changes_source(self) -> None:
        planner_service = _PlannerServiceStub(route="analysis")
        analysis_service = _AnalysisServiceStub(planner_service)
        workflow = build_analysis_workflow(analysis_service=analysis_service)
        existing_plan = PlanningResult(
            route="analysis",
            preprocess_required=False,
            analysis_plan=_make_analysis_plan("dataset-1"),
        ).model_dump()

        result = workflow.invoke(
            {
                "user_input": "정제된 매출 합계",
                "source_id": "dataset-1",
                "dataset_context": _make_dataset_context("dataset-1").model_dump(),
                "guideline_context": {
                    "guideline_source_id": "",
                    "guideline_id": "",
                    "filename": "",
                    "status": "no_active_guideline",
                    "retrieved_chunks": [],
                    "retrieved_count": 0,
                    "has_evidence": False,
                    "evidence_summary": "",
                },
                "planning_result": existing_plan,
                "preprocess_result": {
                    "status": "applied",
                    "output_source_id": "dataset-2",
                },
            }
        )

        self.assertEqual(len(planner_service.plan_calls), 1)
        self.assertEqual(planner_service.plan_calls[0]["source_id"], "dataset-2")
        self.assertEqual(result["dataset_context"]["source_id"], "dataset-2")
        self.assertEqual(
            result["analysis_plan"]["metadata_snapshot"]["columns"],
            ["region", "clean_sales"],
        )
        self.assertEqual(analysis_service.datasets_requested, ["dataset-2"])


if __name__ == "__main__":
    unittest.main()
