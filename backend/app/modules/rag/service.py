from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

from ..datasets.models import Dataset
from ..datasets.repository import DataSourceRepository
from ..guidelines.models import Guideline
from .ai import answer_with_context
from .errors import RagEmbeddingError, RagNotIndexedError, RagSearchError
from .guideline_repository import GuidelineRagRepository
from .repository import RagRepository


@dataclass(frozen=True)
class RetrievedChunk:
    source_id: str
    chunk_id: int
    score: float
    content: str
    db_id: int


class RagService:
    def __init__(
        self,
        *,
        repository: RagRepository,
        storage_dir: Path,
        embedder: Any,
        dataset_repository: DataSourceRepository | None = None,
        answer_agent: Any | None = None,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
        default_model: str = "gpt-5-nano",
    ) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.embedder = embedder
        self.dataset_repository = dataset_repository
        self.answer_agent = answer_agent
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.default_model = default_model
        self.storage_dir.mkdir(parents=True, exist_ok=True)

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

        self.index_dataset(dataset)
        updated_meta = self.repository.get_source(source_id)
        updated_index_path = self._index_path(source_id)
        status = "created" if updated_meta is not None and updated_index_path.exists() else "missing"
        return {"status": status, "source_id": source_id}

    def index_dataset(self, dataset: Dataset) -> None:
        if not dataset.storage_path:
            return
        path = Path(dataset.storage_path)
        if not path.exists():
            return

        checksum = self._checksum_file(path)
        existing = self.repository.get_source(dataset.source_id)
        if existing and existing.checksum == checksum:
            return
        if existing:
            self.delete_source(dataset.source_id)

        text = self._load_text(dataset)
        chunks = self._chunk_text(text)
        if not chunks:
            return

        try:
            embeddings = self.embedder.embed_documents(chunks)
        except Exception as exc:
            raise RagEmbeddingError(str(exc)) from exc

        from .infra.vector_store import FaissStore

        store = FaissStore(dim=self.embedder.embedding_dim)
        faiss_ids = store.add(embeddings)
        index_path = self._index_path(dataset.source_id)
        store.save(index_path)

        self.repository.delete_chunks_by_source(dataset.source_id)
        self.repository.upsert_source(
            source_id=dataset.source_id,
            checksum=checksum,
            embedding_model=self.embedder.model_name,
            embedding_dim=self.embedder.embedding_dim,
            chunk_count=len(chunks),
        )
        self.repository.add_chunks(
            source_id=dataset.source_id,
            chunks=list(zip(range(len(chunks)), chunks, faiss_ids)),
        )

    def query(
        self,
        *,
        query: str,
        top_k: int = 3,
        source_filter: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        sources = self.repository.list_sources(source_filter)
        if not sources:
            raise RagNotIndexedError()

        try:
            query_embedding = self.embedder.embed_query(query)
        except Exception as exc:
            raise RagEmbeddingError(str(exc)) from exc

        scored: List[tuple[float, str, int]] = []
        indexed_sources = 0

        for source in sources:
            index_path = self._index_path(source.source_id)
            if not index_path.exists():
                continue
            indexed_sources += 1
            from .infra.vector_store import FaissStore

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
        parts: List[str] = []
        for item in retrieved:
            parts.append(f"[source:{item.source_id}][chunk:{item.chunk_id}]")
            parts.append(item.content)
        return "\n\n".join(parts)

    def query_for_source(self, *, query: str, source_id: str, top_k: int = 3) -> List[RetrievedChunk]:
        source_meta = self.repository.get_source(source_id)
        index_path = self._index_path(source_id)
        if source_meta is None or not index_path.exists():
            return []
        return self.query(query=query, top_k=top_k, source_filter=[source_id])

    async def answer_query(
        self,
        *,
        query: str,
        top_k: int = 3,
        source_filter: Optional[List[str]] = None,
    ) -> tuple[str, List[RetrievedChunk]] | None:
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

    def add_context_links(self, *, session_id: int, retrieved: Iterable[RetrievedChunk]) -> None:
        by_source: dict[str, List[int]] = {}
        for item in retrieved:
            by_source.setdefault(item.source_id, []).append(item.db_id)
        for source_id, chunk_db_ids in by_source.items():
            self.repository.add_context_entries(
                session_id=session_id,
                source_id=source_id,
                chunk_db_ids=chunk_db_ids,
            )

    def delete_source(self, source_id: str) -> None:
        vector_dir = self.storage_dir / source_id
        if vector_dir.exists():
            shutil.rmtree(vector_dir)
        self.repository.delete_source(source_id)

    def _index_path(self, source_id: str) -> Path:
        return self.storage_dir / source_id / "index.faiss"

    @staticmethod
    def _checksum_file(path: Path) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_text(self, dataset: Dataset) -> str:
        path = Path(dataset.storage_path)
        if path.suffix.lower() == ".pdf":
            return self._load_text_from_file(path=path, max_chars=200000)
        encoding = getattr(dataset, "encoding", None) or "utf-8"
        return path.read_text(encoding=encoding, errors="ignore")

    @staticmethod
    def _load_text_from_file(*, path: Path, max_chars: int) -> str:
        if path.suffix.lower() == ".pdf":
            return RagService._load_pdf(path=path, max_chars=max_chars)
        return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]

    @staticmethod
    def _load_pdf(*, path: Path, max_chars: int) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        chunks: List[str] = []
        total_len = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            if not text.strip():
                continue
            remaining = max_chars - total_len
            if remaining <= 0:
                break
            snippet = text[:remaining]
            chunks.append(snippet)
            total_len += len(snippet)
            if total_len >= max_chars:
                break
        return "\n".join(chunks)

    def _chunk_text(self, text: str) -> List[str]:
        if self.chunk_size <= self.chunk_overlap:
            return [text.strip()] if text.strip() else []

        chunks: List[str] = []
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

    def _load_chunks(self, scored: List[tuple[float, str, int]]) -> List[RetrievedChunk]:
        by_source: dict[str, List[int]] = {}
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

        retrieved: List[RetrievedChunk] = []
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


class GuidelineRagService:
    def __init__(
        self,
        *,
        repository: GuidelineRagRepository,
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

    def index_guideline(self, guideline: Guideline) -> None:
        if not guideline.storage_path:
            return

        path = Path(guideline.storage_path)
        if not path.exists():
            return

        checksum = RagService._checksum_file(path)
        existing = self.repository.get_source(guideline.source_id)
        if existing and existing.checksum == checksum:
            return
        if existing:
            self.delete_source(guideline.source_id)

        text = self._load_text(guideline)
        chunks = self._chunk_text(text)
        if not chunks:
            return

        try:
            embeddings = self.embedder.embed_documents(chunks)
        except Exception as exc:
            raise RagEmbeddingError(str(exc)) from exc

        from .infra.vector_store import FaissStore

        store = FaissStore(dim=self.embedder.embedding_dim)
        faiss_ids = store.add(embeddings)
        index_path = self._index_path(guideline.source_id)
        store.save(index_path)

        self.repository.delete_chunks_by_source(guideline.source_id)
        self.repository.upsert_source(
            source_id=guideline.source_id,
            checksum=checksum,
            embedding_model=self.embedder.model_name,
            embedding_dim=self.embedder.embedding_dim,
            chunk_count=len(chunks),
        )
        self.repository.add_chunks(
            source_id=guideline.source_id,
            chunks=list(zip(range(len(chunks)), chunks, faiss_ids)),
        )

    def query(
        self,
        *,
        query: str,
        top_k: int = 3,
        source_filter: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        sources = self.repository.list_sources(source_filter)
        if not sources:
            raise RagNotIndexedError()

        try:
            query_embedding = self.embedder.embed_query(query)
        except Exception as exc:
            raise RagEmbeddingError(str(exc)) from exc

        scored: List[tuple[float, str, int]] = []
        indexed_sources = 0
        for source in sources:
            index_path = self._index_path(source.source_id)
            if not index_path.exists():
                continue
            indexed_sources += 1

            from .infra.vector_store import FaissStore

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
        parts: List[str] = []
        for item in retrieved:
            parts.append(f"[source:{item.source_id}][chunk:{item.chunk_id}]")
            parts.append(item.content)
        return "\n\n".join(parts)

    def add_context_links(self, *, session_id: int, retrieved: Iterable[RetrievedChunk]) -> None:
        by_source: dict[str, List[int]] = {}
        for item in retrieved:
            by_source.setdefault(item.source_id, []).append(item.db_id)
        for source_id, chunk_db_ids in by_source.items():
            self.repository.add_context_entries(
                session_id=session_id,
                source_id=source_id,
                chunk_db_ids=chunk_db_ids,
            )

    def delete_source(self, source_id: str) -> None:
        vector_dir = self.storage_dir / source_id
        if vector_dir.exists():
            shutil.rmtree(vector_dir)
        self.repository.delete_source(source_id)

    def _index_path(self, source_id: str) -> Path:
        return self.storage_dir / source_id / "index.faiss"

    def _load_text(self, guideline: Guideline) -> str:
        path = Path(guideline.storage_path)
        return RagService._load_text_from_file(path=path, max_chars=200000)

    def _chunk_text(self, text: str) -> List[str]:
        if self.chunk_size <= self.chunk_overlap:
            return [text.strip()] if text.strip() else []

        chunks: List[str] = []
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

    def _load_chunks(self, scored: List[tuple[float, str, int]]) -> List[RetrievedChunk]:
        by_source: dict[str, List[int]] = {}
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

        retrieved: List[RetrievedChunk] = []
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
