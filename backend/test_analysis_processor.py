from __future__ import annotations

import unittest

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import AnalysisPlanDraft, MetadataSnapshot


class AnalysisProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.processor = AnalysisProcessor()
        self.metadata = MetadataSnapshot(
            columns=[
                "PassengerId",
                "Survived",
                "Pclass",
                "Name",
                "Sex",
                "Age",
                "SibSp",
                "Parch",
                "Ticket",
                "Fare",
                "Cabin",
                "Embarked",
            ],
            dtypes={
                "PassengerId": "int64",
                "Survived": "int64",
                "Pclass": "int64",
                "Name": "object",
                "Sex": "object",
                "Age": "float64",
                "SibSp": "int64",
                "Parch": "int64",
                "Ticket": "object",
                "Fare": "float64",
                "Cabin": "object",
                "Embarked": "object",
            },
            numeric_columns=["PassengerId", "Survived", "Pclass", "Age", "SibSp", "Parch", "Fare"],
            categorical_columns=["Name", "Sex", "Ticket", "Cabin", "Embarked"],
            datetime_columns=[],
            row_count=891,
        )

    def _build_missing_value_draft(self, synthetic_token: str) -> AnalysisPlanDraft:
        return AnalysisPlanDraft.model_validate(
            {
                "analysis_type": "missing_values_analysis",
                "objective": "결측치 현황을 요약하고 전처리 계획을 제안한다.",
                "filters": [{"column": "column_type", "operator": "not_null"}],
                "group_by": [synthetic_token],
                "metrics": [
                    {
                        "name": "missing_rate",
                        "aggregation": "rate",
                        "column": "Age",
                        "alias": "missing_rate_Age",
                    },
                    {
                        "name": "missing_rate",
                        "aggregation": "rate",
                        "column": "Cabin",
                        "alias": "missing_rate_Cabin",
                    },
                ],
                "visualization_hint": {
                    "preferred_chart": "bar",
                    "x": synthetic_token,
                    "y": "missing_rate_Age",
                    "series": "feature_type",
                    "caption": "Missing value rates per column",
                },
                "ambiguity_status": "clear",
            }
        )

    def test_missing_value_plan_ignores_synthetic_dimensions(self) -> None:
        for synthetic_token in ("column", "column_type", "column_names"):
            with self.subTest(synthetic_token=synthetic_token):
                plan = self.processor.validate_and_finalize_plan(
                    self._build_missing_value_draft(synthetic_token),
                    self.metadata,
                )

                self.assertEqual(plan.group_by, [])
                self.assertEqual(plan.filters, [])
                self.assertEqual(plan.visualization_hint.preferred_chart, "none")
                self.assertIsNone(plan.visualization_hint.x)
                self.assertIsNone(plan.visualization_hint.series)
                self.assertEqual(plan.required_columns, ["Age", "Cabin"])

    def test_non_missing_value_plan_rejects_synthetic_dimension(self) -> None:
        draft = AnalysisPlanDraft.model_validate(
            {
                "analysis_type": "descriptive_analysis",
                "objective": "연령 평균을 요약한다.",
                "group_by": ["column_type"],
                "metrics": [
                    {
                        "name": "average_age",
                        "aggregation": "avg",
                        "column": "Age",
                        "alias": "average_age",
                    }
                ],
                "ambiguity_status": "clear",
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "planning used synthetic grouping dimension: column_type",
        ):
            self.processor.validate_and_finalize_plan(draft, self.metadata)

    def test_non_synthetic_unknown_column_still_fails(self) -> None:
        draft = AnalysisPlanDraft.model_validate(
            {
                "analysis_type": "descriptive_analysis",
                "objective": "사망률을 요약한다.",
                "group_by": ["mortality_rate"],
                "metrics": [
                    {
                        "name": "average_age",
                        "aggregation": "avg",
                        "column": "Age",
                        "alias": "average_age",
                    }
                ],
                "ambiguity_status": "clear",
            }
        )

        with self.assertRaisesRegex(
            ValueError,
            "column not found in dataset metadata: mortality_rate",
        ):
            self.processor.validate_and_finalize_plan(draft, self.metadata)


if __name__ == "__main__":
    unittest.main()
