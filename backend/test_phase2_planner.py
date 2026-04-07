import unittest

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisExecutionResult,
    AnalysisPlanDraft,
    MetricSpec,
    QuestionUnderstanding,
)
from backend.app.modules.analysis.service import AnalysisService
from backend.app.modules.planner.dependencies import get_planner_service
from backend.app.modules.planner.schemas import PlannerDecision, PlanningResult
from backend.app.modules.planner.service import (
    PlannerService,
    build_handoff_from_planning_result,
    build_preprocess_decision_from_planning_result,
)
from backend.app.modules.profiling.schemas import DatasetContext


class _DatasetContextServiceStub:
    def build_context(self, source_id: str) -> DatasetContext:
        return DatasetContext(
            source_id=source_id,
            filename="sales.csv",
            available=True,
            row_count_total=120,
            row_count_sample=3,
            column_count=3,
            columns=["date", "region", "sales"],
            dtypes={"date": "object", "region": "object", "sales": "int64"},
            logical_types={"date": "datetime", "region": "categorical", "sales": "numerical"},
            type_columns={
                "numerical": ["sales"],
                "categorical": ["region"],
                "datetime": ["date"],
                "boolean": [],
                "identifier": [],
                "group_key": [],
            },
            numeric_columns=["sales"],
            datetime_columns=["date"],
            categorical_columns=["region"],
            boolean_columns=[],
            identifier_columns=[],
            group_key_columns=[],
            sample_rows=[],
            missing_rates={"region": 0.1},
        )


class _StubPlannerService(PlannerService):
    def __init__(
        self,
        *,
        decision: PlannerDecision,
        understanding: QuestionUnderstanding,
        plan_draft: AnalysisPlanDraft,
    ) -> None:
        super().__init__(
            dataset_context_service=_DatasetContextServiceStub(),
            analysis_processor=AnalysisProcessor(),
        )
        self._decision = decision
        self._understanding = understanding
        self._plan_draft = plan_draft

    def _build_decision(self, **kwargs) -> PlannerDecision:
        return self._decision

    def _build_question_understanding(self, **kwargs) -> QuestionUnderstanding:
        return self._understanding

    def _build_analysis_plan_draft(self, **kwargs) -> AnalysisPlanDraft:
        return self._plan_draft


class _PlannerServiceRunStub:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def plan(self, **kwargs) -> PlanningResult:
        self.calls.append(kwargs)
        analysis_plan = _StubPlannerService(
            decision=PlannerDecision(ask_analysis=True),
            understanding=QuestionUnderstanding(ambiguity_status="clear"),
            plan_draft=AnalysisPlanDraft(
                analysis_type="aggregation",
                objective="sales 합계",
                metrics=[
                    MetricSpec(
                        name="sales",
                        aggregation="sum",
                        column="sales",
                        alias="total_sales",
                    )
                ],
                ambiguity_status="clear",
            ),
        ).plan(
            user_input="sales 합계",
            request_context=None,
            source_id="dataset-1",
        ).analysis_plan
        return PlanningResult(route="analysis", analysis_plan=analysis_plan)


class _DatasetModelStub:
    def __init__(self, source_id: str, storage_path: str = "/tmp/sample.csv") -> None:
        self.source_id = source_id
        self.storage_path = storage_path


class _DatasetRepositoryStubForRun:
    def get_by_source_id(self, source_id: str):
        return _DatasetModelStub(source_id)


class _UnusedStub:
    pass


class PlannerPhase2Tests(unittest.TestCase):
    def test_plan_without_source_id_routes_to_general_question(self) -> None:
        service = _StubPlannerService(
            decision=PlannerDecision(),
            understanding=QuestionUnderstanding(ambiguity_status="clear"),
            plan_draft=AnalysisPlanDraft(
                analysis_type="aggregation",
                objective="noop",
                metrics=[
                    MetricSpec(
                        name="sales",
                        aggregation="sum",
                        column="sales",
                        alias="total_sales",
                    )
                ],
                ambiguity_status="clear",
            ),
        )

        result = service.plan(
            user_input="안녕",
            request_context=None,
            source_id=None,
        )

        self.assertEqual(result.route, "general_question")
        self.assertFalse(result.preprocess_required)
        self.assertIsNone(result.analysis_plan)

    def test_plan_can_route_dataset_selected_request_to_general_question(self) -> None:
        service = _StubPlannerService(
            decision=PlannerDecision(is_general_question=True),
            understanding=QuestionUnderstanding(ambiguity_status="clear"),
            plan_draft=AnalysisPlanDraft(
                analysis_type="aggregation",
                objective="noop",
                metrics=[
                    MetricSpec(
                        name="sales",
                        aggregation="sum",
                        column="sales",
                        alias="total_sales",
                    )
                ],
                ambiguity_status="clear",
            ),
        )

        result = service.plan(
            user_input="파이썬이 뭐야?",
            request_context=None,
            source_id="dataset-1",
        )

        self.assertEqual(result.route, "general_question")
        self.assertIsNone(result.analysis_plan)

    def test_plan_builds_analysis_plan_when_analysis_route_is_required(self) -> None:
        service = _StubPlannerService(
            decision=PlannerDecision(
                ask_analysis=True,
                preprocess_required=True,
                need_visualization=True,
                need_report=True,
                guideline_context_used=True,
            ),
            understanding=QuestionUnderstanding(
                analysis_goal=["aggregate"],
                metric_keywords=["sales"],
                group_keywords=["region"],
                ambiguity_status="clear",
            ),
            plan_draft=AnalysisPlanDraft(
                analysis_type="aggregation",
                objective="region별 sales 합계",
                group_by=["region"],
                metrics=[
                    MetricSpec(
                        name="sales",
                        aggregation="sum",
                        column="sales",
                        alias="total_sales",
                    )
                ],
                ambiguity_status="clear",
            ),
        )

        result = service.plan(
            user_input="지역별 매출 합계를 보여줘",
            request_context="차트도 같이 보고 싶어",
            source_id="dataset-1",
            guideline_context={
                "guideline_source_id": "guideline-1",
                "guideline_id": "g-1",
                "filename": "policy.md",
                "status": "retrieved",
                "retrieved_chunks": [{"chunk_id": "c-1"}],
                "retrieved_count": 1,
                "has_evidence": True,
                "evidence_summary": "매출 집계 기준은 최신 정책을 따른다.",
            },
        )

        self.assertEqual(result.route, "analysis")
        self.assertTrue(result.preprocess_required)
        self.assertTrue(result.need_visualization)
        self.assertTrue(result.need_report)
        self.assertTrue(result.guideline_context_used)
        self.assertIsNotNone(result.analysis_plan)
        self.assertEqual(result.analysis_plan.group_by, ["region"])
        self.assertIn("sales", result.analysis_plan.required_columns)

    def test_plan_returns_clarification_without_analysis_plan_when_question_is_ambiguous(self) -> None:
        service = _StubPlannerService(
            decision=PlannerDecision(ask_analysis=True),
            understanding=QuestionUnderstanding(
                analysis_goal=["aggregate"],
                ambiguity_status="needs_clarification",
                clarification_message="어떤 지표를 볼지 구체적으로 알려주세요.",
            ),
            plan_draft=AnalysisPlanDraft(
                analysis_type="aggregation",
                objective="noop",
                metrics=[
                    MetricSpec(
                        name="sales",
                        aggregation="sum",
                        column="sales",
                        alias="total_sales",
                    )
                ],
                ambiguity_status="clear",
            ),
        )

        result = service.plan(
            user_input="분석해줘",
            request_context=None,
            source_id="dataset-1",
        )

        self.assertEqual(result.route, "analysis")
        self.assertTrue(result.needs_clarification)
        self.assertEqual(result.clarification_question, "어떤 지표를 볼지 구체적으로 알려주세요.")
        self.assertIsNone(result.analysis_plan)

    def test_compatibility_adapters_follow_planning_result(self) -> None:
        planning_result = PlanningResult(
            route="analysis",
            preprocess_required=True,
            need_visualization=True,
            need_report=False,
            guideline_context_used=True,
        )

        handoff = build_handoff_from_planning_result(planning_result)
        preprocess_decision = build_preprocess_decision_from_planning_result(planning_result)

        self.assertEqual(handoff["next_step"], "analysis")
        self.assertTrue(handoff["ask_analysis"])
        self.assertTrue(handoff["ask_preprocess"])
        self.assertTrue(handoff["ask_visualization"])
        self.assertFalse(handoff["ask_report"])
        self.assertTrue(handoff["ask_guideline"])
        self.assertEqual(preprocess_decision["step"], "run_preprocess")

    def test_analysis_service_run_passes_full_planner_input_contract(self) -> None:
        dataset_context_service = _DatasetContextServiceStub()
        planner_service = _PlannerServiceRunStub()
        service = AnalysisService(
            dataset_repository=_DatasetRepositoryStubForRun(),
            dataset_context_service=dataset_context_service,
            planner_service=planner_service,
            run_service=_UnusedStub(),
            processor=_UnusedStub(),
            sandbox=_UnusedStub(),
        )
        service._run_code_generation_loop = lambda **kwargs: {
            "generated_code": "print('ok')",
            "validated_code": "print('ok')",
            "sandbox_result": {"ok": True},
            "analysis_result": AnalysisExecutionResult(
                execution_status="success",
                summary="ok",
                table=[],
                raw_metrics={"total_sales": 10},
                used_columns=["sales"],
            ),
            "analysis_error": None,
            "final_status": "success",
        }
        service._build_visualization_output = lambda **kwargs: None
        service._persist_result = lambda **kwargs: "result-1"

        guideline_context = {
            "guideline_source_id": "guideline-1",
            "guideline_id": "g-1",
            "filename": "policy.md",
            "status": "retrieved",
            "retrieved_chunks": [],
            "retrieved_count": 0,
            "has_evidence": True,
            "evidence_summary": "최신 정책을 적용합니다.",
        }
        service.run(
            question="지역별 매출 합계를 보여줘",
            source_id="dataset-1",
            session_id="123",
            request_context="차트도 같이 보고 싶어",
            guideline_context=guideline_context,
            model_id="gpt-5-nano",
        )

        self.assertEqual(len(planner_service.calls), 1)
        self.assertEqual(planner_service.calls[0]["request_context"], "차트도 같이 보고 싶어")
        self.assertEqual(planner_service.calls[0]["guideline_context"], guideline_context)
        self.assertEqual(planner_service.calls[0]["dataset_context"].source_id, "dataset-1")

    def test_planner_dependency_is_available(self) -> None:
        self.assertTrue(callable(get_planner_service))


if __name__ == "__main__":
    unittest.main()
