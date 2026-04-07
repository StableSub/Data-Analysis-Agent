import unittest
from unittest.mock import patch

from backend.app.modules.analysis.schemas import (
    AnalysisPlan,
    ExpectedOutputSpec,
    MetadataSnapshot,
    MetricSpec,
    VisualizationHint,
)
from backend.app.modules.reports.service import ReportService
from backend.app.orchestration.state_view import build_merged_context
from backend.app.orchestration.workflows.visualization import build_visualization_workflow


def _make_analysis_plan() -> AnalysisPlan:
    return AnalysisPlan(
        analysis_type="aggregation",
        objective="sales 합계",
        required_columns=["sales"],
        used_columns=["sales"],
        filters=[],
        group_by=[],
        metrics=[
            MetricSpec(
                name="sales",
                aggregation="sum",
                column="sales",
                alias="total_sales",
            )
        ],
        derived_columns=[],
        sort_by=[],
        time_context=None,
        expected_output=ExpectedOutputSpec(),
        visualization_hint=VisualizationHint(preferred_chart="bar", x="region", y="sales"),
        empty_result_policy="success_with_empty_table",
        metadata_snapshot=MetadataSnapshot(
            columns=["region", "sales"],
            dtypes={"region": "object", "sales": "int64"},
            numeric_columns=["sales"],
            datetime_columns=[],
            categorical_columns=["region"],
            row_count=120,
        ),
        codegen_strategy="llm_codegen",
    )


class _ReportRepositoryStub:
    def create(self, report):
        return report


class _VisualizationServiceStub:
    def __init__(self) -> None:
        self.analysis_build_calls: list[dict] = []
        self.load_calls: list[dict] = []

    def build_from_analysis_result(self, *, source_id: str, analysis_plan, analysis_result):
        self.analysis_build_calls.append(
            {
                "source_id": source_id,
                "analysis_plan": analysis_plan,
                "analysis_result": analysis_result,
            }
        )
        return {
            "status": "generated",
            "source_id": source_id,
            "summary": "analysis 결과를 바탕으로 bar 시각화를 생성했습니다.",
            "chart_data": {
                "chart_type": "bar",
                "x": ["A", "B"],
                "series": [{"name": "sales", "y": [10, 20]}],
                "caption": "region별 sales",
            },
        }

    def load_sample_frame(self, source_id: str, *, nrows: int):
        self.load_calls.append({"source_id": source_id, "nrows": nrows})
        return None, "dataset_missing"


class Phase4DownstreamTests(unittest.TestCase):
    def test_report_service_builds_draft_from_analysis_result_context_only(self) -> None:
        service = ReportService(_ReportRepositoryStub())
        analysis_result = {
            "summary": "region별 sales 합계를 계산했습니다.",
            "table": [{"region": "A", "sales": 10}],
            "raw_metrics": {"total_sales": 10},
            "used_columns": ["region", "sales"],
            "execution_status": "success",
        }
        visualization_result = {
            "status": "generated",
            "summary": "bar 차트를 생성했습니다.",
            "chart_data": {"chart_type": "bar", "caption": "region별 sales"},
        }
        guideline_context = {
            "status": "retrieved",
            "has_evidence": True,
            "retrieved_count": 2,
            "evidence_summary": "최신 집계 기준을 적용합니다.",
            "filename": "policy.md",
        }
        dataset_context = {
            "source_id": "dataset-1",
            "filename": "sales.csv",
            "row_count_total": 120,
            "column_count": 2,
            "columns": ["region", "sales"],
            "quality_summary": {
                "missing_total": 3,
                "missing_ratio": 0.0125,
                "top_missing_columns": [{"column": "sales", "missing_rate": 0.01}],
            },
        }

        with patch(
            "backend.app.modules.reports.service.draft_report",
            return_value="요약\n...\n핵심 인사이트\n...\n권고사항\n...",
        ) as mocked_draft:
            draft = service.build_report_draft(
                question="매출 리포트를 작성해줘",
                analysis_result=analysis_result,
                visualization_result=visualization_result,
                guideline_context=guideline_context,
                dataset_context=dataset_context,
                revision_instruction="",
                model_id=None,
            )

        self.assertEqual(draft["status"], "generated")
        self.assertEqual(draft["metrics"]["primary_source"], "analysis_result.raw_metrics")
        self.assertEqual(draft["metrics"]["primary_metrics"], {"total_sales": 10})
        payload = mocked_draft.call_args.kwargs["report_payload"]
        self.assertEqual(payload["analysis_result"]["summary"], analysis_result["summary"])
        self.assertEqual(payload["visualization_result"]["chart_type"], "bar")
        self.assertEqual(payload["guideline_context"]["evidence_summary"], "최신 집계 기준을 적용합니다.")
        self.assertEqual(payload["dataset_context"]["filename"], "sales.csv")

    def test_report_metrics_priority_falls_back_to_table_then_quality_summary(self) -> None:
        service = ReportService(_ReportRepositoryStub())

        table_metrics = service.build_metrics_from_results(
            analysis_result={
                "table": [{"region": "A", "sales": 10}, {"region": "B", "sales": 20}],
                "used_columns": ["region", "sales"],
                "execution_status": "success",
            },
            dataset_context={"quality_summary": {"missing_total": 5}},
        )
        quality_metrics = service.build_metrics_from_results(
            analysis_result={"execution_status": "success"},
            dataset_context={"quality_summary": {"missing_total": 5}},
        )

        self.assertEqual(table_metrics["primary_source"], "analysis_result.table")
        self.assertEqual(table_metrics["primary_metrics"]["row_count"], 2)
        self.assertEqual(quality_metrics["primary_source"], "dataset_context.quality_summary")
        self.assertEqual(quality_metrics["primary_metrics"], {"missing_total": 5})

    def test_visualization_workflow_skips_replanning_when_analysis_result_exists(self) -> None:
        service = _VisualizationServiceStub()
        workflow = build_visualization_workflow(visualization_service=service)

        result = workflow.invoke(
            {
                "user_input": "지역별 매출을 차트로 보여줘",
                "source_id": "dataset-1",
                "analysis_plan": _make_analysis_plan().model_dump(),
                "analysis_result": {
                    "summary": "region별 sales 합계를 계산했습니다.",
                    "table": [{"region": "A", "sales": 10}, {"region": "B", "sales": 20}],
                    "raw_metrics": {"total_sales": 30},
                    "used_columns": ["region", "sales"],
                    "execution_status": "success",
                },
            }
        )

        self.assertEqual(len(service.analysis_build_calls), 1)
        self.assertEqual(service.load_calls, [])
        self.assertEqual(result["visualization_plan"]["status"], "analysis_generated")
        self.assertEqual(result["visualization_result"]["status"], "generated")

    def test_merged_context_contains_analysis_first_downstream_inputs(self) -> None:
        merged_context = build_merged_context(
            {
                "dataset_context": {"source_id": "dataset-1"},
                "guideline_context": {"status": "retrieved", "has_evidence": True},
                "analysis_result": {"execution_status": "success", "summary": "ok"},
                "visualization_result": {"status": "generated"},
            }
        )

        self.assertIn("dataset_context", merged_context)
        self.assertIn("guideline_context", merged_context)
        self.assertIn("analysis_result", merged_context)
        self.assertIn("visualization_result", merged_context)
        self.assertEqual(
            merged_context["applied_steps"],
            ["guideline", "analysis", "visualization"],
        )


if __name__ == "__main__":
    unittest.main()
