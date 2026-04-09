import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from backend.app.modules.datasets.service import DatasetReader
from backend.app.modules.eda.service import EDAService
from backend.app.modules.profiling.schemas import DatasetProfile


class _FakeProfileService:
    def __init__(self, profile: DatasetProfile) -> None:
        self.profile = profile

    def build_profile(self, source_id: str) -> DatasetProfile:
        return self.profile


class _FakeRepository:
    def __init__(self, storage_path: str) -> None:
        self.dataset = SimpleNamespace(storage_path=storage_path)

    def get_by_source_id(self, source_id: str):
        return self.dataset


def _build_profile(source_id: str, column: str) -> DatasetProfile:
    return DatasetProfile(
        source_id=source_id,
        available=True,
        row_count=0,
        sample_row_count=0,
        column_count=1,
        columns=[column],
        numeric_columns=[column],
        logical_types={column: "numerical"},
    )


class EdaDistributionLabelTest(unittest.TestCase):
    def _build_service(self, values: list[float], column: str = "Age") -> EDAService:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        file_path = Path(temp_dir.name) / "dataset.csv"
        pd.DataFrame({column: values}).to_csv(file_path, index=False)
        profile = _build_profile("src-test", column)
        return EDAService(
            profile_service=_FakeProfileService(profile),
            dataset_repository=_FakeRepository(str(file_path)),
            reader=DatasetReader(),
        )

    def test_integer_like_distribution_uses_discrete_integer_labels(self) -> None:
        values = list(range(20)) + [31.5]
        service = self._build_service(values)

        distribution = service.get_distribution("src-test", column="Age", bins=4)

        self.assertIsNotNone(distribution)
        labels = [item.label for item in distribution.bins]
        self.assertTrue(all(label.isdigit() for label in labels))
        self.assertEqual(labels[:4], ["0", "1", "2", "3"])
        self.assertEqual(sum(item.value for item in distribution.bins), len(values))

    def test_integer_like_threshold_accepts_ninety_five_percent(self) -> None:
        values = list(range(19)) + [19.5]
        service = self._build_service(values)

        distribution = service.get_distribution("src-test", column="Age", bins=4)

        self.assertIsNotNone(distribution)
        self.assertTrue(all(item.label.isdigit() for item in distribution.bins))

    def test_below_integer_like_threshold_keeps_float_labels(self) -> None:
        values = list(range(18)) + [18.5, 19.5]
        service = self._build_service(values)

        distribution = service.get_distribution("src-test", column="Age", bins=4)

        self.assertIsNotNone(distribution)
        self.assertTrue(any("." in item.label for item in distribution.bins))

    def test_continuous_distribution_keeps_float_labels(self) -> None:
        values = [0.1, 1.2, 2.4, 3.8, 4.9, 5.3, 6.7, 7.1, 8.6, 9.9]
        service = self._build_service(values, column="Fare")

        distribution = service.get_distribution("src-test", column="Fare", bins=4)

        self.assertIsNotNone(distribution)
        self.assertTrue(any("." in item.label for item in distribution.bins))


if __name__ == "__main__":
    unittest.main()
