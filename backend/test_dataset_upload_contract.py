from __future__ import annotations

import io
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

from backend.app.modules.datasets.models import Dataset
from backend.app.modules.datasets.router import get_dataset_sample
from backend.app.modules.datasets.service import DatasetReadError, DatasetReader, DatasetService, DatasetStorage
from backend.app.modules.eda.router import get_eda_profile
from backend.app.modules.preprocess.router import apply as apply_preprocess
from backend.app.modules.preprocess.schemas import PreprocessApplyRequest
from backend.app.modules.profiling.service import DatasetProfileService


class _FakeDatasetRepository:
    def __init__(self) -> None:
        self.created: list[Dataset] = []
        self.datasets_by_source: dict[str, Dataset] = {}

    def create(self, dataset: Dataset) -> Dataset:
        dataset.id = len(self.created) + 1
        dataset.source_id = dataset.source_id or str(uuid.uuid4())
        self.created.append(dataset)
        self.datasets_by_source[dataset.source_id] = dataset
        return dataset

    def get_by_source_id(self, source_id: str) -> Dataset | None:
        return self.datasets_by_source.get(source_id)


class _BrokenSampleService:
    def get_dataset_sample(self, source_id: str, n_rows: int = 5):
        raise DatasetReadError("broken")


class _BrokenPreprocessService:
    def apply(self, source_id: str, operations):
        raise DatasetReadError("broken")


class _BrokenEdaService:
    def get_profile(self, source_id: str):
        raise DatasetReadError("broken")


class _DatasetRepositoryForProfile:
    def __init__(self, dataset: Dataset) -> None:
        self.dataset = dataset

    def get_by_source_id(self, source_id: str) -> Dataset | None:
        if source_id == self.dataset.source_id:
            return self.dataset
        return None


class DatasetUploadContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage_dir = Path(self.tempdir.name)
        self.repository = _FakeDatasetRepository()
        self.reader = DatasetReader()
        self.service = DatasetService(
            repository=self.repository,
            storage=DatasetStorage(self.storage_dir),
            reader=self.reader,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_upload_rejects_non_csv_files_before_persisting(self) -> None:
        with self.assertRaisesRegex(ValueError, "CSV 파일만 업로드할 수 있습니다."):
            self.service.upload_dataset(
                file_stream=io.BytesIO(b"not really an xlsx"),
                original_filename="report.xlsx",
            )

        self.assertEqual(self.repository.created, [])
        self.assertEqual(list(self.storage_dir.iterdir()), [])

    def test_upload_rejects_non_utf8_csv_and_cleans_temp_file(self) -> None:
        with self.assertRaisesRegex(ValueError, "UTF-8 CSV만 업로드할 수 있습니다."):
            self.service.upload_dataset(
                file_stream=io.BytesIO("name\n가\n".encode("cp949")),
                original_filename="legacy.csv",
            )

        self.assertEqual(self.repository.created, [])
        self.assertEqual(list(self.storage_dir.iterdir()), [])

    def test_upload_accepts_utf8_csv(self) -> None:
        dataset = self.service.upload_dataset(
            file_stream=io.BytesIO("name,value\nalpha,1\n".encode("utf-8")),
            original_filename="clean.csv",
        )

        self.assertEqual(len(self.repository.created), 1)
        self.assertEqual(dataset.filename, "clean.csv")
        self.assertTrue(Path(dataset.storage_path).exists())

    def test_profile_raises_shared_dataset_read_error_for_unreadable_file(self) -> None:
        unreadable_path = self.storage_dir / "legacy.csv"
        unreadable_path.write_bytes(b"name\nok\n" + "가\n".encode("cp949"))
        dataset = Dataset(
            id=1,
            source_id="legacy-source",
            filename="legacy.csv",
            storage_path=str(unreadable_path),
            filesize=unreadable_path.stat().st_size,
        )
        profile_service = DatasetProfileService(
            repository=_DatasetRepositoryForProfile(dataset),
            reader=self.reader,
        )

        with self.assertRaises(DatasetReadError):
            profile_service.build_profile("legacy-source", sample_rows=1)


class DatasetReadErrorRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_dataset_sample_returns_422_for_unreadable_dataset(self) -> None:
        with self.assertRaises(HTTPException) as context:
            await get_dataset_sample(
                source_id="broken",
                service=_BrokenSampleService(),
            )

        self.assertEqual(context.exception.status_code, 422)

    async def test_preprocess_apply_returns_422_for_unreadable_dataset(self) -> None:
        request = PreprocessApplyRequest(source_id="broken", operations=[])

        with self.assertRaises(HTTPException) as context:
            apply_preprocess(req=request, service=_BrokenPreprocessService())

        self.assertEqual(context.exception.status_code, 422)

    async def test_eda_profile_returns_422_for_unreadable_dataset(self) -> None:
        with self.assertRaises(HTTPException) as context:
            get_eda_profile(source_id="broken", service=_BrokenEdaService())

        self.assertEqual(context.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
