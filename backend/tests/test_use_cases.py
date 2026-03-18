from __future__ import annotations

import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.app.modules.chat.models import ChatMessage, ChatSession
from backend.app.modules.chat.run_service import ChatRunService
from backend.app.modules.chat.service import ChatService
from backend.app.modules.chat.session_service import ChatSessionService
from backend.app.modules.datasets.models import Dataset
from backend.app.modules.datasets.service import DataSourceService
from backend.app.modules.export.service import ExportService
from backend.app.modules.preprocess.service import PreprocessService
from backend.app.modules.rag.service import RetrievedChunk
from backend.app.modules.reports.service import ReportService


class FakeChatRepository:
    def __init__(self) -> None:
        self.sessions: dict[int, ChatSession] = {}
        self.messages: list[ChatMessage] = []
        self.next_session_id = 1
        self.next_message_id = 1

    def get_session(self, session_id: int) -> ChatSession | None:
        return self.sessions.get(session_id)

    def create_session(self, title: str | None = None) -> ChatSession:
        session = ChatSession(id=self.next_session_id, title=title)
        self.sessions[self.next_session_id] = session
        self.next_session_id += 1
        return session

    def append_message(self, session: ChatSession, role: str, content: str) -> ChatMessage:
        message = ChatMessage(
            id=self.next_message_id,
            session_id=session.id,
            role=role,
            content=content,
            created_at=datetime.utcnow(),
        )
        self.messages.append(message)
        self.next_message_id += 1
        return message

    def get_history(self, session_id: int) -> list[ChatMessage]:
        return [message for message in self.messages if message.session_id == session_id]

    def delete_session(self, session_id: int) -> bool:
        return self.sessions.pop(session_id, None) is not None


class FakeDatasetRepository:
    def __init__(self) -> None:
        self.items: dict[str, Dataset] = {}
        self.next_id = 1

    def create(self, dataset: Dataset) -> Dataset:
        dataset.id = self.next_id
        if not dataset.source_id:
            dataset.source_id = f"source-{self.next_id}"
        self.items[dataset.source_id] = dataset
        self.next_id += 1
        return dataset

    def list_all(self) -> list[Dataset]:
        return list(self.items.values())

    def get_by_id(self, dataset_id: int) -> Dataset | None:
        for dataset in self.items.values():
            if dataset.id == dataset_id:
                return dataset
        return None

    def get_by_source_id(self, source_id: str) -> Dataset | None:
        return self.items.get(source_id)

    def delete(self, dataset: Dataset) -> None:
        self.items.pop(dataset.source_id, None)


class FakeAiOrchestrator:
    async def astream_with_trace(self, **_: object):
        yield {
            "type": "thought",
            "step": {
                "phase": "analysis",
                "message": "질문을 해석했습니다.",
                "status": "completed",
            },
        }
        yield {"type": "chunk", "delta": "부분 응답 "}
        yield {
            "type": "done",
            "answer": "최종 응답",
            "thought_steps": [
                {
                    "phase": "analysis",
                    "message": "질문을 해석했습니다.",
                    "status": "completed",
                }
            ],
        }

    def get_pending_approval(self, *, run_id: str):
        return None


class FakeApprovalAiOrchestrator:
    def __init__(self) -> None:
        self.pending = {
            "stage": "preprocess",
            "kind": "plan_review",
            "title": "Preprocess plan review",
            "summary": "검토가 필요합니다.",
            "source_id": "source-1",
            "plan": {"operations": []},
            "draft": "",
            "review": {},
        }

    async def astream_with_trace(self, **_: object):
        yield {
            "type": "approval_required",
            "pending_approval": self.pending,
            "thought_steps": [
                {
                    "phase": "analysis",
                    "message": "검토 단계로 이동했습니다.",
                    "status": "completed",
                }
            ],
        }

    def get_pending_approval(self, *, run_id: str):
        return self.pending


class FakeDatasetStorage:
    def __init__(self) -> None:
        self.saved: list[tuple[bytes, str]] = []

    def persist_file(self, file_stream, filename: str) -> tuple[Path, int]:
        payload = file_stream.read()
        self.saved.append((payload, filename))
        return Path(f"/tmp/{filename}"), len(payload)

    def delete_file(self, storage_path: str) -> None:
        return None


class FakeDatasetIndexer:
    def __init__(self) -> None:
        self.indexed: list[Dataset] = []

    def index_dataset(self, dataset: Dataset) -> None:
        self.indexed.append(dataset)

    def delete_source(self, source_id: str) -> None:
        return None


class FakeDatasetReader:
    def __init__(self, frame: pd.DataFrame) -> None:
        self.frame = frame

    def read_csv(self, storage_path: str, **_: object) -> pd.DataFrame:
        return self.frame.copy()


class FakePreprocessProcessor:
    def apply_operations(self, df: pd.DataFrame, operations: list[object]) -> pd.DataFrame:
        return df.assign(processed=True)


class FakeReportRepository:
    def create(self, report):
        report.id = "report-1"
        return report

    def get(self, report_id: str):
        return None

    def list_by_session(self, session_id: int):
        return []


class FakeAgentForSummary:
    async def astream_with_trace(self, **_: object):
        yield {"type": "chunk", "delta": "요약 "}
        yield {"type": "done", "answer": "요약 리포트"}


class FakeResultsRepository:
    def get_analysis_result_data(self, result_id: str):
        return [{"date": "2024-01-01", "sales": 100}]


class FakeRagService:
    def query(self, *, query: str, top_k: int = 3, source_filter=None):
        return [
            RetrievedChunk(
                source_id="source-1",
                chunk_id=0,
                score=0.99,
                content="매출은 증가했습니다.",
                db_id=1,
            )
        ]

    def build_context(self, retrieved):
        return "context"

    async def answer_query(self, *, query: str, top_k: int = 3, source_filter=None):
        return "요약 리포트", self.query(query=query, top_k=top_k, source_filter=source_filter)


class ChatServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_ask_creates_session_and_persists_messages(self):
        chat_repository = FakeChatRepository()
        dataset_repository = FakeDatasetRepository()
        dataset_repository.items["source-1"] = Dataset(
            id=1,
            source_id="source-1",
            filename="sales.csv",
            storage_path="/tmp/sales.csv",
            filesize=10,
        )
        session_service = ChatSessionService(chat_repository)
        run_service = ChatRunService(
            agent=FakeAiOrchestrator(),
            repository=chat_repository,
            session_service=session_service,
            data_source_repository=dataset_repository,
        )
        service = ChatService(
            session_service=session_service,
            run_service=run_service,
        )

        result = await service.ask(
            question="매출 추세가 어때?",
            source_id="source-1",
        )

        self.assertEqual(result.answer, "최종 응답")
        self.assertEqual(result.session_id, 1)
        self.assertEqual(len(chat_repository.messages), 2)
        self.assertEqual(chat_repository.messages[0].role, "user")
        self.assertEqual(chat_repository.messages[1].role, "assistant")

    async def test_ask_returns_pending_approval_when_agent_requires_approval(self):
        chat_repository = FakeChatRepository()
        dataset_repository = FakeDatasetRepository()
        dataset_repository.items["source-1"] = Dataset(
            id=1,
            source_id="source-1",
            filename="sales.csv",
            storage_path="/tmp/sales.csv",
            filesize=10,
        )
        session_service = ChatSessionService(chat_repository)
        run_service = ChatRunService(
            agent=FakeApprovalAiOrchestrator(),
            repository=chat_repository,
            session_service=session_service,
            data_source_repository=dataset_repository,
        )
        service = ChatService(
            session_service=session_service,
            run_service=run_service,
        )

        result = await service.ask(
            question="전처리 제안 보여줘",
            source_id="source-1",
        )

        self.assertEqual(result.answer, "")
        self.assertEqual(result.session_id, 1)
        self.assertIsNotNone(result.run_id)
        self.assertIsNotNone(result.pending_approval)
        self.assertEqual(result.pending_approval.stage, "preprocess")
        self.assertEqual(chat_repository.messages[0].role, "user")
        self.assertEqual(len(chat_repository.messages), 1)

    def test_get_pending_approval_maps_schema(self):
        chat_repository = FakeChatRepository()
        session_service = ChatSessionService(chat_repository)
        session = session_service.get_or_create_session(session_id=None, title="approval")
        run_service = ChatRunService(
            agent=FakeApprovalAiOrchestrator(),
            repository=chat_repository,
            session_service=session_service,
            data_source_repository=FakeDatasetRepository(),
        )

        pending = run_service.get_pending_approval(
            session_id=session.id,
            run_id="run-1",
        )

        self.assertIsNotNone(pending)
        self.assertEqual(pending.session_id, session.id)
        self.assertEqual(pending.run_id, "run-1")
        self.assertEqual(pending.pending_approval.stage, "preprocess")


class DatasetAndPreprocessServiceTest(unittest.TestCase):
    def test_upload_dataset_persists_file_and_indexes_dataset(self):
        repository = FakeDatasetRepository()
        storage = FakeDatasetStorage()
        indexer = FakeDatasetIndexer()
        service = DataSourceService(
            repository=repository,
            storage=storage,
            reader=FakeDatasetReader(pd.DataFrame()),
            rag_service=indexer,
        )

        dataset = service.upload_dataset(
            file_stream=io.BytesIO(b"date,sales\n2024-01-01,100\n"),
            original_filename="sales.csv",
            display_name="sales.csv",
        )

        self.assertEqual(dataset.filename, "sales.csv")
        self.assertEqual(dataset.storage_path, "/tmp/sales.csv")
        self.assertEqual(len(storage.saved), 1)
        self.assertEqual(len(indexer.indexed), 1)

    def test_get_dataset_sample_returns_preview_data(self):
        repository = FakeDatasetRepository()
        dataset = repository.create(
            Dataset(
                filename="sales.csv",
                storage_path="/tmp/sales.csv",
                filesize=10,
            )
        )
        service = DataSourceService(
            repository=repository,
            storage=FakeDatasetStorage(),
            reader=FakeDatasetReader(pd.DataFrame([{"date": "2024-01-01", "sales": 100}])),
        )

        sample = service.get_dataset_sample(source_id=dataset.source_id, n_rows=5)

        self.assertIsNotNone(sample)
        self.assertEqual(sample["columns"], ["date", "sales"])
        self.assertEqual(sample["rows"][0]["sales"], 100)

    def test_apply_preprocess_creates_new_dataset(self):
        repository = FakeDatasetRepository()
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "sales.csv"
            source_path.write_text("date,sales\n2024-01-01,100\n", encoding="utf-8")
            input_dataset = repository.create(
                Dataset(
                    filename="sales.csv",
                    storage_path=str(source_path),
                    filesize=10,
                )
            )
            service = PreprocessService(
                repository=repository,
                reader=FakeDatasetReader(pd.DataFrame([{"date": "2024-01-01", "sales": 100}])),
                processor=FakePreprocessProcessor(),
            )

            result = service.apply(source_id=input_dataset.source_id, operations=[])

            self.assertEqual(result.input_source_id, input_dataset.source_id)
            self.assertTrue(result.output_filename.startswith("sales_preprocessed_"))


class ReportExportRagFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_report_summary_and_persist(self):
        service = ReportService(FakeReportRepository(), agent=FakeAgentForSummary())
        result = await service.create_report_from_request(
            session_id=1,
            analysis_results=[{"sales": 100}],
            visualizations=[],
            insights=[],
        )

        self.assertEqual(result.id, "report-1")
        self.assertEqual(result.summary_text, "요약 리포트")

    async def test_generate_rag_answer_returns_answer_and_chunks(self):
        result = await FakeRagService().answer_query(
            query="최근 매출 추세는?",
        )

        self.assertIsNotNone(result)
        answer, retrieved = result
        self.assertEqual(answer, "요약 리포트")
        self.assertEqual(retrieved[0].source_id, "source-1")

    async def test_export_csv_serializes_rows(self):
        service = ExportService(FakeResultsRepository())

        content, filename = service.export_csv("result-1")

        self.assertIsNotNone(content)
        self.assertIsNotNone(filename)
        self.assertIn("result_", filename)
        self.assertIn("sales", content.getvalue().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
