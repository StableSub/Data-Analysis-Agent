from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from ..ai.agents.client import AgentClient
from ..domain.data_source.models import Dataset
from .core.embedding import E5Embedder
from .core.vector_store import FaissStore
from .repository import RagRepository
from .types.errors import RagEmbeddingError, RagNotIndexedError, RagSearchError


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
        embedder: E5Embedder,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def index_dataset(self, dataset: Dataset) -> None:
        """
        데이터셋 파일을 읽어 벡터 인덱스 및 DB 구축.
        """
        if not dataset.storage_path:
            return

        path = Path(dataset.storage_path)
        if not path.exists():
            return

        # 중복 처리 방지
        checksum = self._checksum_file(path)
        existing = self.repository.get_source(dataset.source_id)
        if existing and existing.checksum == checksum:
            return

        # 기존 인덱스가 있다면 삭제 후 재생성
        if existing:
            self.delete_source(dataset.source_id)

        # 텍스트 추출 및 청킹
        text = self._load_text(dataset)
        chunks = self._chunk_text(text)
        if not chunks:
            return

        # 임베딩 생성
        try:
            embeddings = self.embedder.embed_documents(chunks)
        except Exception as exc:
            raise RagEmbeddingError(str(exc)) from exc

        # FAISS 인덱스 생성 및 로컬 파일 저장
        store = FaissStore(dim=self.embedder.embedding_dim)
        faiss_ids = store.add(embeddings)

        index_path = self._index_path(dataset.source_id)
        store.save(index_path)

        # DB 메타데이터 및 청크 내용 저장
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
        """
        질문과 유사한 청크를 벡터 스토어에서 검색.
        """
        sources = self.repository.list_sources(source_filter)
        if not sources:
            raise RagNotIndexedError()

        try:
            query_embedding = self.embedder.embed_query(query)
        except Exception as exc:
            raise RagEmbeddingError(str(exc)) from exc

        scored: List[tuple[float, str, int]] = []
        indexed_sources = 0

        # 각 소스별 FAISS 인덱스 로드 및 검색
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

            # 유효한 검색 결과 수집
            for score, faiss_id in zip(scores[0], ids[0]):
                if faiss_id < 0:
                    continue
                scored.append((float(score), source.source_id, int(faiss_id)))

        if indexed_sources == 0:
            raise RagNotIndexedError()

        if not scored:
            return []

        # 전체 결과 중 유사도 순 정렬 후 상위 k개 선정
        scored.sort(key=lambda item: item[0], reverse=True)
        scored = scored[:top_k]

        # DB에서 실제 텍스트 내용 조회 및 병합
        chunks = self._load_chunks(scored)
        return chunks

    def build_context(self, retrieved: Iterable[RetrievedChunk]) -> str:
        parts: List[str] = []
        for item in retrieved:
            parts.append(f"[source:{item.source_id}][chunk:{item.chunk_id}]")
            parts.append(item.content)
        return "\n\n".join(parts)

    def add_context_links(
        self, *, session_id: int, retrieved: Iterable[RetrievedChunk]
    ) -> None:
        """
        대화 세션과 참조한 청크 간의 관계 저장.
        """
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

    def _checksum_file(self, path: Path) -> str:
        """파일 변경 감지를 위한 SHA-256 해시 계산."""
        hasher = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_text(self, dataset: Dataset) -> str:
        """파일 확장자에 따른 텍스트 추출."""
        path = Path(dataset.storage_path)
        if path.suffix.lower() == ".pdf":
            return AgentClient.load_text_from_file(str(path), max_chars=200000)
        encoding = getattr(dataset, "encoding", None) or "utf-8"
        return path.read_text(encoding=encoding, errors="ignore")

    def _chunk_text(self, text: str) -> List[str]:
        """텍스트 분할"""
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

    def _load_chunks(
        self, scored: List[tuple[float, str, int]]
    ) -> List[RetrievedChunk]:
        """FAISS 검색 결과를 이용해 DB에서 청크 원문 조회 및 매핑."""
        # DB 조회를 최소화하기 위해 소스별로 ID 그룹화
        by_source: dict[str, List[int]] = {}
        for _, source_id, faiss_id in scored:
            by_source.setdefault(source_id, []).append(faiss_id)

        # DB 조회 결과를 (source_id, faiss_id) 키로 매핑
        chunk_map: dict[tuple[str, int], RetrievedChunk] = {}
        for source_id, faiss_ids in by_source.items():
            rows = self.repository.get_chunks_by_faiss_ids(source_id, faiss_ids)
            for row in rows:
                key = (source_id, row.faiss_id)
                chunk_map[key] = RetrievedChunk(
                    source_id=source_id,
                    chunk_id=row.chunk_id,
                    score=0.0,
                    content=row.content,
                    db_id=row.id,
                )

        # 검색된 순서와 점수를 유지하며 결과 리스트 구성
        results: List[RetrievedChunk] = []
        for score, source_id, faiss_id in scored:
            key = (source_id, faiss_id)
            item = chunk_map.get(key)
            if item:
                results.append(
                    RetrievedChunk(
                        source_id=item.source_id,
                        chunk_id=item.chunk_id,
                        score=score,
                        content=item.content,
                        db_id=item.db_id,
                    )
                )
        return results
