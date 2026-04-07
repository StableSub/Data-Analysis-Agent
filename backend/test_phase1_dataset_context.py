import unittest

from backend.app.modules.analysis.schemas import MetadataSnapshot
from backend.app.modules.analysis.service import AnalysisService
from backend.app.modules.profiling.schemas import ColumnProfile, DatasetContext, DatasetProfile
from backend.app.modules.profiling.service import DatasetContextService


class _DatasetRecord:
    def __init__(self, *, source_id: str, filename: str, storage_path: str = "/tmp/sample.csv") -> None:
        self.source_id = source_id
        self.filename = filename
        self.storage_path = storage_path


class _DatasetRepositoryStub:
    def __init__(self, dataset=None) -> None:
        self.dataset = dataset
        self.calls: list[str] = []

    def get_by_source_id(self, source_id: str):
        self.calls.append(source_id)
        if self.dataset is not None and self.dataset.source_id == source_id:
            return self.dataset
        return None


class _ProfileServiceStub:
    def __init__(self, profile: DatasetProfile) -> None:
        self.profile = profile
        self.calls: list[str] = []

    def build_profile(self, source_id: str) -> DatasetProfile:
        self.calls.append(source_id)
        return self.profile


class _DatasetContextServiceStub:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def build_context(self, source_id: str) -> DatasetContext:
        self.calls.append(source_id)
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
            missing_rates={},
        )


class _UnusedStub:
    pass


class _PlannerServiceStub:
    pass


class Phase1DatasetContextTests(unittest.TestCase):
    def test_dataset_context_service_builds_shared_contract(self) -> None:
        repository = _DatasetRepositoryStub(
            _DatasetRecord(source_id="dataset-1", filename="sales.csv")
        )
        profile = DatasetProfile(
            source_id="dataset-1",
            available=True,
            row_count=120,
            sample_row_count=3,
            column_count=3,
            columns=["date", "region", "sales"],
            dtypes={"date": "object", "region": "object", "sales": "int64"},
            missing_rates={"date": 0.0, "region": 0.1, "sales": 0.05},
            sample_rows=[
                {"date": "2024-01-01", "region": "Seoul", "sales": 10},
                {"date": "2024-01-02", "region": None, "sales": 20},
                {"date": "2024-01-03", "region": "Busan", "sales": None},
            ],
            numeric_columns=["sales"],
            datetime_columns=["date"],
            categorical_columns=["region"],
            boolean_columns=[],
            identifier_columns=[],
            group_key_columns=["region"],
            type_columns={
                "numerical": ["sales"],
                "categorical": ["region"],
                "datetime": ["date"],
                "boolean": [],
                "identifier": [],
                "group_key": ["region"],
            },
            logical_types={"date": "datetime", "region": "group_key", "sales": "numerical"},
            column_profiles=[
                ColumnProfile(
                    name="date",
                    raw_dtype="object",
                    inferred_type="datetime",
                    null_count=0,
                    missing_rate=0.0,
                    unique_count=120,
                    unique_ratio=1.0,
                    sample_values=["2024-01-01"],
                ),
                ColumnProfile(
                    name="region",
                    raw_dtype="object",
                    inferred_type="group_key",
                    null_count=12,
                    missing_rate=0.1,
                    unique_count=4,
                    unique_ratio=0.0333,
                    sample_values=["Seoul", "Busan"],
                ),
                ColumnProfile(
                    name="sales",
                    raw_dtype="int64",
                    inferred_type="numerical",
                    null_count=6,
                    missing_rate=0.05,
                    unique_count=80,
                    unique_ratio=0.6667,
                    sample_values=[10, 20],
                ),
            ],
        )
        service = DatasetContextService(
            repository=repository,
            profile_service=_ProfileServiceStub(profile),
        )

        context = service.build_context("dataset-1")

        self.assertTrue(context.available)
        self.assertEqual(context.filename, "sales.csv")
        self.assertEqual(context.row_count_total, 120)
        self.assertEqual(context.row_count_sample, 3)
        self.assertEqual(context.numeric_columns, ["sales"])
        self.assertEqual(context.datetime_columns, ["date"])
        self.assertEqual(context.group_key_columns, ["region"])
        self.assertEqual(context.quality_summary.missing_total, 18)
        self.assertEqual(context.quality_summary.missing_ratio, 0.05)
        self.assertEqual(
            [item.column for item in context.quality_summary.top_missing_columns],
            ["region", "sales"],
        )

    def test_analysis_build_dataset_metadata_adapts_dataset_context(self) -> None:
        dataset_context_service = _DatasetContextServiceStub()
        service = AnalysisService(
            dataset_repository=_DatasetRepositoryStub(),
            dataset_context_service=dataset_context_service,
            planner_service=_PlannerServiceStub(),
            run_service=_UnusedStub(),
            processor=_UnusedStub(),
            sandbox=_UnusedStub(),
        )

        metadata = service.build_dataset_metadata("dataset-1")

        self.assertIsInstance(metadata, MetadataSnapshot)
        self.assertEqual(dataset_context_service.calls, ["dataset-1"])
        self.assertEqual(metadata.columns, ["date", "region", "sales"])
        self.assertEqual(metadata.numeric_columns, ["sales"])
        self.assertEqual(metadata.datetime_columns, ["date"])
        self.assertEqual(metadata.categorical_columns, ["region"])
        self.assertEqual(metadata.row_count, 120)

    def test_profiling_dependency_module_imports_after_wiring_fix(self) -> None:
        from backend.app.modules.profiling.dependencies import get_dataset_context_service

        self.assertTrue(callable(get_dataset_context_service))


if __name__ == "__main__":
    unittest.main()
