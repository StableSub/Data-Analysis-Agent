from __future__ import annotations

import hashlib
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Iterable, Optional

from ..datasets.models import Dataset
from ..datasets.repository import DatasetRepository
from ..datasets.service import DatasetService
from ..guidelines.models import Guideline
from ..guidelines.service import GuidelineService
from .ai import answer_with_context
from .errors import RagEmbeddingError, RagNotIndexedError, RagSearchError
from .guideline_repository import GuidelineRagRepository
from .repository import RagRepository

MAX_INDEX_TEXT_CHARS = 200_000
SUPPORTED_DATASET_RAG_EXTENSIONS = {".csv", ".json", ".txt", ".md", ".pdf"}


@dataclass(frozen=True)
class RetrievedChunk:
    source_id: str
    chunk_id: int
    score: float
    content: str
    db_id: int


class _BaseIndexedRagService:
    def __init__(
        self,
        *,
        repository: RagRepository | GuidelineRagRepository,
        storage_dir: Path,
        embedder: Any,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def query(
        self,
        *,
        query: str,
        top_k: int = 3,
        source_filter: Optional[list[str]] = None,
    ) -> list[RetrievedChunk]:
        sources = self.repository.list_sources(source_filter)
        if not sources:
            raise RagNotIndexedError()

        try:
            query_embedding = self.embedder.embed_query(query)
        except Exception as exc:
            raise RagEmbeddingError(str(exc)) from exc

        from .infra.vector_store import FaissStore

        scored: list[tuple[float, str, int]] = []
        indexed_sources = 0
        for source in sources:
            index_path = self._index_path(source.source_id)
            if not index_path.exists():
                continue

            indexed_sources += 1
            store = FaissStore.load(index_path)
            try:
                scores, ids = store.search(query_embedding, top_k)
            except Exception as exc:
                raise RagSearchError(str(exc)) from exc

            for score, faiss_id in zip(scores[0], ids[0]):
                if faiss_id < 0:
                    continue
                scored.append((float(score), source.source_id, int(faiss_id)))

        if indexed_sources == 0:
            raise RagNotIndexedError()
        if not scored:
            return []

        scored.sort(key=lambda item: item[0], reverse=True)
        return self._load_chunks(scored[:top_k])

    def build_context(self, retrieved: Iterable[RetrievedChunk]) -> str:
        parts: list[str] = []
        for item in retrieved:
            parts.append(f"[source:{item.source_id}][chunk:{item.chunk_id}]")
            parts.append(item.content)
        return "\n\n".join(parts)

    def query_for_source(self, *, query: str, source_id: str, top_k: int = 3) -> list[RetrievedChunk]:
        source_meta = self.repository.get_source(source_id)
        index_path = self._index_path(source_id)
        if source_meta is None or not index_path.exists():
            return []
        return self.query(query=query, top_k=top_k, source_filter=[source_id])

    def delete_source(self, source_id: str) -> None:
        self._remove_dir(self._source_dir(source_id))
        self.repository.delete_source(source_id)

    def _replace_source_index(
        self,
        *,
        source_id: str,
        checksum: str,
        chunks: list[str],
    ) -> None:
        chunk_rows, temp_dir = self._build_temp_index(source_id=source_id, chunks=chunks)
        final_dir = self._source_dir(source_id)
        backup_dir = self._backup_dir(source_id)

        try:
            self._remove_dir(backup_dir)
            if final_dir.exists():
                final_dir.rename(backup_dir)
            temp_dir.rename(final_dir)
        except Exception:
            self._remove_dir(temp_dir)
            if backup_dir.exists() and not final_dir.exists():
                backup_dir.rename(final_dir)
            raise

        try:
            self.repository.replace_source_contents(
                source_id=source_id,
                checksum=checksum,
                embedding_model=self.embedder.model_name,
                embedding_dim=self.embedder.embedding_dim,
                chunks=chunk_rows,
            )
        except Exception:
            self._remove_dir(final_dir)
            if backup_dir.exists():
                backup_dir.rename(final_dir)
            raise

        self._remove_dir(backup_dir)

    def _build_temp_index(
        self,
        *,
        source_id: str,
        chunks: list[str],
    ) -> tuple[list[tuple[int, str, int]], Path]:
        from .infra.vector_store import FaissStore

        temp_dir = self._temp_dir(source_id)
        self._remove_dir(temp_dir)

        store = FaissStore(dim=self.embedder.embedding_dim)
        faiss_ids: list[int] = []
        if chunks:
            try:
                embeddings = self.embedder.embed_documents(chunks)
            except Exception as exc:
                raise RagEmbeddingError(str(exc)) from exc
            faiss_ids = store.add(embeddings)

        store.save(temp_dir / "index.faiss")
        chunk_rows = list(zip(range(len(chunks)), chunks, faiss_ids))
        return chunk_rows, temp_dir

    def _source_dir(self, source_id: str) -> Path:
        return self.storage_dir / source_id

    def _index_path(self, source_id: str) -> Path:
        return self._source_dir(source_id) / "index.faiss"

    def _temp_dir(self, source_id: str) -> Path:
        return self.storage_dir / f".{source_id}.{uuid.uuid4().hex}.tmp"

    def _backup_dir(self, source_id: str) -> Path:
        return self.storage_dir / f".{source_id}.bak"

    @staticmethod
    def _remove_dir(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path)

    @staticmethod
    def _checksum_file(path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _load_text_from_file(*, path: Path, max_chars: int = MAX_INDEX_TEXT_CHARS) -> str:
        if path.suffix.lower() == ".pdf":
            return _BaseIndexedRagService._load_pdf(path=path, max_chars=max_chars)
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]

    @staticmethod
    def _load_pdf(*, path: Path, max_chars: int) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts: list[str] = []
        total_len = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            if not text.strip():
                continue
            remaining = max_chars - total_len
            if remaining <= 0:
                break
            snippet = text[:remaining]
            parts.append(snippet)
            total_len += len(snippet)
            if total_len >= max_chars:
                break
        return "\n".join(parts)

    def _chunk_text(self, text: str) -> list[str]:
        if self.chunk_size <= self.chunk_overlap:
            return [text.strip()] if text.strip() else []

        chunks: list[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(length, start + self.chunk_size)
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= length:
                break
            start = max(0, end - self.chunk_overlap)
        return chunks

    def _load_chunks(self, scored: list[tuple[float, str, int]]) -> list[RetrievedChunk]:
        by_source: dict[str, list[int]] = {}
        for _, source_id, faiss_id in scored:
            by_source.setdefault(source_id, []).append(faiss_id)

        chunk_map: dict[tuple[str, int], RetrievedChunk] = {}
        for source_id, faiss_ids in by_source.items():
            rows = self.repository.get_chunks_by_faiss_ids(source_id, faiss_ids)
            for row in rows:
                chunk_map[(source_id, row.faiss_id)] = RetrievedChunk(
                    source_id=source_id,
                    chunk_id=row.chunk_id,
                    score=0.0,
                    content=row.content,
                    db_id=row.id,
                )

        retrieved: list[RetrievedChunk] = []
        for score, source_id, faiss_id in scored:
            item = chunk_map.get((source_id, faiss_id))
            if item is None:
                continue
            retrieved.append(
                RetrievedChunk(
                    source_id=item.source_id,
                    chunk_id=item.chunk_id,
                    score=score,
                    content=item.content,
                    db_id=item.db_id,
                )
            )
        return retrieved


class RagService(_BaseIndexedRagService):
    def __init__(
        self,
        *,
        repository: RagRepository,
        storage_dir: Path,
        embedder: Any,
        dataset_repository: DatasetRepository | None = None,
        answer_agent: Any | None = None,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        default_model: str = "gpt-5-nano",
    ) -> None:
        super().__init__(
            repository=repository,
            storage_dir=storage_dir,
            embedder=embedder,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.dataset_repository = dataset_repository
        self.answer_agent = answer_agent
        self.default_model = default_model

    def ensure_index_for_source(self, source_id: str) -> dict[str, str]:
        if not source_id:
            return {"status": "no_source"}
        if self.dataset_repository is None:
            return {"status": "dataset_missing", "source_id": source_id}

        dataset = self.dataset_repository.get_by_source_id(source_id)
        if dataset is None:
            return {"status": "dataset_missing", "source_id": source_id}

        source_meta = self.repository.get_source(source_id)
        index_path = self._index_path(source_id)
        if source_meta is not None and index_path.exists():
            return {"status": "existing", "source_id": source_id}

        if not self._is_supported_dataset(dataset):
            return {"status": "unsupported_format", "source_id": source_id}

        self.index_dataset(dataset)
        updated_meta = self.repository.get_source(source_id)
        updated_index_path = self._index_path(source_id)
        status = "created" if updated_meta is not None and updated_index_path.exists() else "missing"
        return {"status": status, "source_id": source_id}

    def index_dataset(self, dataset: Dataset) -> None:
        if not dataset.storage_path:
            return

        path = Path(dataset.storage_path)
        if not path.exists() or not self._is_supported_dataset(dataset):
            return

        checksum = self._checksum_file(path)
        existing = self.repository.get_source(dataset.source_id)
        if existing and existing.checksum == checksum and self._index_path(dataset.source_id).exists():
            return

        text = self._load_dataset_text(path)
        chunks = self._chunk_text(text)
        self._replace_source_index(
            source_id=dataset.source_id,
            checksum=checksum,
            chunks=chunks,
        )

    async def answer_query(
        self,
        *,
        query: str,
        top_k: int = 3,
        source_filter: Optional[list[str]] = None,
    ) -> tuple[str, list[RetrievedChunk]] | None:
        retrieved = self.query(query=query, top_k=top_k, source_filter=source_filter)
        if not retrieved:
            return None

        context = self.build_context(retrieved)
        if self.answer_agent is not None:
            answer_parts: list[str] = []
            final_answer: str | None = None
            async for event in self.answer_agent.astream_with_trace(question=query, context=context):
                event_type = event.get("type")
                if event_type == "chunk":
                    delta = event.get("delta")
                    if isinstance(delta, str) and delta:
                        answer_parts.append(delta)
                elif event_type == "done":
                    done_answer = event.get("answer")
                    if isinstance(done_answer, str):
                        final_answer = done_answer

            answer = final_answer if final_answer is not None else "".join(answer_parts)
        else:
            answer = answer_with_context(
                query=query,
                context=context,
                model_id=None,
                default_model=self.default_model,
            )
        return answer, retrieved

    @staticmethod
    def _is_supported_dataset(dataset: Dataset) -> bool:
        if not dataset.storage_path:
            return False
        return Path(dataset.storage_path).suffix.lower() in SUPPORTED_DATASET_RAG_EXTENSIONS

    @staticmethod
    def _load_dataset_text(path: Path) -> str:
        return _BaseIndexedRagService._load_text_from_file(path=path)


class GuidelineRagService(_BaseIndexedRagService):
    def __init__(
        self,
        *,
        repository: GuidelineRagRepository,
        storage_dir: Path,
        embedder: Any,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> None:
        super().__init__(
            repository=repository,
            storage_dir=storage_dir,
            embedder=embedder,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def ensure_index_for_guideline(self, guideline: Guideline) -> dict[str, str]:
        source_id = guideline.source_id
        source_meta = self.repository.get_source(source_id)
        index_path = self._index_path(source_id)
        if source_meta is not None and index_path.exists():
            return {"status": "existing", "source_id": source_id}

        self.index_guideline(guideline)
        updated_meta = self.repository.get_source(source_id)
        updated_index_path = self._index_path(source_id)
        status = (
            "created"
            if updated_meta is not None and updated_index_path.exists()
            else "missing"
        )
        return {"status": status, "source_id": source_id}

    def index_guideline(self, guideline: Guideline) -> None:
        if not guideline.storage_path:
            return

        path = Path(guideline.storage_path)
        if not path.exists():
            return

        checksum = self._checksum_file(path)
        existing = self.repository.get_source(guideline.source_id)
        if existing and existing.checksum == checksum and self._index_path(guideline.source_id).exists():
            return

        text = self._load_guideline_text(path)
        chunks = self._chunk_text(text)
        self._replace_source_index(
            source_id=guideline.source_id,
            checksum=checksum,
            chunks=chunks,
        )

    @staticmethod
    def _load_guideline_text(path: Path) -> str:
        return _BaseIndexedRagService._load_text_from_file(path=path)


class DatasetRagSyncService:
    def __init__(
        self,
        *,
        dataset_service: DatasetService,
        rag_service: RagService,
    ) -> None:
        self.dataset_service = dataset_service
        self.rag_service = rag_service

    def upload_dataset(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: str | None = None,
    ) -> Dataset:
        dataset = self.dataset_service.upload_dataset(
            file_stream=file_stream,
            original_filename=original_filename,
            display_name=display_name,
        )
        try:
            self.rag_service.index_dataset(dataset)
        except Exception:
            try:
                self.rag_service.delete_source(dataset.source_id)
            except Exception:
                pass
            self.dataset_service.delete_dataset(dataset.source_id)
            raise
        return dataset

    def delete_dataset(self, source_id: str) -> bool:
        deleted = self.dataset_service.delete_dataset(source_id)
        if not deleted:
            return False
        try:
            self.rag_service.delete_source(source_id)
        except Exception:
            pass
        return True


class GuidelineRagSyncService:
    def __init__(
        self,
        *,
        guideline_service: GuidelineService,
        guideline_rag_service: GuidelineRagService,
    ) -> None:
        self.guideline_service = guideline_service
        self.guideline_rag_service = guideline_rag_service

    def upload_guideline(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: str | None = None,
        content_type: str | None = None,
    ) -> Guideline:
        guideline = self.guideline_service.upload_guideline(
            file_stream=file_stream,
            original_filename=original_filename,
            display_name=display_name,
            content_type=content_type,
        )
        try:
            self.guideline_rag_service.index_guideline(guideline)
        except Exception:
            try:
                self.guideline_rag_service.delete_source(guideline.source_id)
            except Exception:
                pass
            self.guideline_service.delete_guideline(guideline.source_id)
            raise
        return guideline

    def delete_guideline(self, source_id: str) -> bool:
        deleted = self.guideline_service.delete_guideline(source_id)
        if not deleted:
            return False
        try:
            self.guideline_rag_service.delete_source(source_id)
        except Exception:
            pass
        return True
