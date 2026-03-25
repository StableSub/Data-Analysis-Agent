from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from .models import RagChunk, RagContext, RagSource


class RagRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_source(self, source_id: str) -> Optional[RagSource]:
        return self.db.query(RagSource).filter(RagSource.source_id == source_id).first()

    def list_sources(self, source_filter: Optional[List[str]] = None) -> List[RagSource]:
        query = self.db.query(RagSource)
        if source_filter:
            query = query.filter(RagSource.source_id.in_(source_filter))
        return query.all()

    def upsert_source(
        self,
        *,
        source_id: str,
        checksum: str,
        embedding_model: str,
        embedding_dim: int,
        chunk_count: int,
    ) -> RagSource:
        source = self.get_source(source_id)
        if source is None:
            source = RagSource(
                source_id=source_id,
                checksum=checksum,
                embedding_model=embedding_model,
                embedding_dim=embedding_dim,
                chunk_count=chunk_count,
            )
            self.db.add(source)
        else:
            source.checksum = checksum
            source.embedding_model = embedding_model
            source.embedding_dim = embedding_dim
            source.chunk_count = chunk_count
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete_source(self, source_id: str) -> None:
        source = self.get_source(source_id)
        if source:
            self.db.delete(source)
            self.db.commit()

    def delete_chunks_by_source(self, source_id: str) -> None:
        self.db.query(RagChunk).filter(RagChunk.source_id == source_id).delete(
            synchronize_session=False
        )
        self.db.commit()

    def add_chunks(
        self,
        *,
        source_id: str,
        chunks: Iterable[tuple[int, str, int]],
    ) -> List[RagChunk]:
        objects = [
            RagChunk(source_id=source_id, chunk_id=chunk_id, content=content, faiss_id=faiss_id)
            for chunk_id, content, faiss_id in chunks
        ]
        self.db.add_all(objects)
        self.db.commit()
        return objects

    def get_chunks_by_faiss_ids(self, source_id: str, faiss_ids: List[int]) -> List[RagChunk]:
        return (
            self.db.query(RagChunk)
            .filter(RagChunk.source_id == source_id, RagChunk.faiss_id.in_(faiss_ids))
            .all()
        )

    def add_context_entries(
        self,
        *,
        session_id: int,
        source_id: str,
        chunk_db_ids: Iterable[int],
    ) -> None:
        objects = [
            RagContext(session_id=session_id, source_id=source_id, chunk_id=chunk_db_id)
            for chunk_db_id in chunk_db_ids
        ]
        self.db.add_all(objects)
        self.db.commit()
