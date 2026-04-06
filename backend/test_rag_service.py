import unittest
from dataclasses import fields

from backend.app.modules.rag.service import (
    DatasetRagSyncService,
    GuidelineRagSyncService,
    RetrievedChunk,
)


class _DatasetServiceStub:
    def __init__(self, *, delete_error: Exception | None = None) -> None:
        self.delete_error = delete_error
        self.calls: list[str] = []

    def get_dataset_detail(self, source_id: str):
        self.calls.append(f"get:{source_id}")
        return object()

    def delete_dataset(self, source_id: str) -> bool:
        self.calls.append(f"delete:{source_id}")
        if self.delete_error is not None:
            raise self.delete_error
        return True


class _RagServiceStub:
    def __init__(self, *, delete_error: Exception | None = None) -> None:
        self.delete_error = delete_error
        self.calls: list[str] = []

    def delete_source(self, source_id: str) -> None:
        self.calls.append(f"delete:{source_id}")
        if self.delete_error is not None:
            raise self.delete_error


class _GuidelineServiceStub:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def delete_guideline(self, source_id: str) -> bool:
        self.calls.append(f"delete:{source_id}")
        return True


class RagServiceTests(unittest.TestCase):
    def test_dataset_delete_runs_primary_delete_before_rag_cleanup(self) -> None:
        dataset_service = _DatasetServiceStub()
        rag_service = _RagServiceStub()
        sync_service = DatasetRagSyncService(
            dataset_service=dataset_service,
            rag_service=rag_service,
        )

        deleted = sync_service.delete_dataset("dataset-1")

        self.assertTrue(deleted)
        self.assertEqual(dataset_service.calls, ["get:dataset-1", "delete:dataset-1"])
        self.assertEqual(rag_service.calls, ["delete:dataset-1"])

    def test_dataset_delete_does_not_cleanup_rag_when_primary_delete_fails(self) -> None:
        dataset_service = _DatasetServiceStub(delete_error=RuntimeError("delete failed"))
        rag_service = _RagServiceStub()
        sync_service = DatasetRagSyncService(
            dataset_service=dataset_service,
            rag_service=rag_service,
        )

        with self.assertRaisesRegex(RuntimeError, "delete failed"):
            sync_service.delete_dataset("dataset-1")

        self.assertEqual(rag_service.calls, [])

    def test_guideline_delete_surfaces_rag_cleanup_failure(self) -> None:
        guideline_service = _GuidelineServiceStub()
        guideline_rag_service = _RagServiceStub(delete_error=RuntimeError("rag cleanup failed"))
        sync_service = GuidelineRagSyncService(
            guideline_service=guideline_service,
            guideline_rag_service=guideline_rag_service,
        )

        with self.assertRaisesRegex(RuntimeError, "rag cleanup failed"):
            sync_service.delete_guideline("guideline-1")

        self.assertEqual(guideline_service.calls, ["delete:guideline-1"])
        self.assertEqual(guideline_rag_service.calls, ["delete:guideline-1"])

    def test_retrieved_chunk_fields_do_not_include_db_id(self) -> None:
        field_names = [field.name for field in fields(RetrievedChunk)]

        self.assertEqual(field_names, ["source_id", "chunk_id", "score", "content"])


if __name__ == "__main__":
    unittest.main()
