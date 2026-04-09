import unittest

import numpy as np
import pandas as pd

from backend.app.modules.eda.schemas import PreprocessRecommendation, RecommendedOperation
from backend.app.modules.preprocess.processor import PreprocessProcessor
from backend.app.modules.preprocess.schemas import DerivedColumnOperation
from backend.app.modules.preprocess.service import PreprocessService


class DerivedColumnProcessorTest(unittest.TestCase):
    def test_log1p_operation_creates_new_column(self) -> None:
        processor = PreprocessProcessor()
        frame = pd.DataFrame({"Fare": [0.0, 9.0, 99.0]})

        result = processor.apply_operations(
            frame,
            [
                DerivedColumnOperation(
                    op="derived_column",
                    name="Fare_log1p",
                    source_columns=["Fare"],
                    transform_type="log1p",
                    params=None,
                ),
            ],
        )

        self.assertIn("Fare_log1p", result.columns)
        self.assertAlmostEqual(result.loc[1, "Fare_log1p"], np.log1p(9.0))

    def test_ratio_operation_uses_nan_for_zero_division(self) -> None:
        processor = PreprocessProcessor()
        frame = pd.DataFrame({"Fare": [10.0, 20.0], "Family": [2.0, 0.0]})

        result = processor.apply_operations(
            frame,
            [
                DerivedColumnOperation(
                    op="derived_column",
                    name="Fare_per_family",
                    source_columns=["Fare", "Family"],
                    transform_type="ratio",
                    params={"zero_division": "null"},
                ),
            ],
        )

        self.assertEqual(result.loc[0, "Fare_per_family"], 5.0)
        self.assertTrue(pd.isna(result.loc[1, "Fare_per_family"]))


class DerivedColumnRecommendationTranslationTest(unittest.TestCase):
    def test_recommendation_translates_to_derived_column_operation(self) -> None:
        service = PreprocessService.__new__(PreprocessService)

        operations = service._recommendation_to_operations(  # type: ignore[attr-defined]
            recommendation=PreprocessRecommendation(
                summary="Fare log1p를 만듭니다.",
                operations=[
                    RecommendedOperation(
                        op="derived_column",
                        target_columns=["Fare_log1p"],
                        source_columns=["Fare"],
                        target_column="Fare_log1p",
                        transform_type="log1p",
                        params=None,
                        reason="왜도가 높아 로그 변환 권장",
                        priority="high",
                    ),
                ],
            ),
            numeric_columns={"Fare"},
        )

        self.assertEqual(len(operations), 1)
        derived = operations[0]
        self.assertEqual(derived.op, "derived_column")
        self.assertEqual(derived.name, "Fare_log1p")
        self.assertEqual(derived.source_columns, ["Fare"])
        self.assertEqual(derived.transform_type, "log1p")


if __name__ == "__main__":
    unittest.main()
