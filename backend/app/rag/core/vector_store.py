from __future__ import annotations

from pathlib import Path
from typing import Tuple

import faiss
import numpy as np


class FaissStore:
    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)

    def add(self, embeddings: np.ndarray) -> list[int]:
        start = self.index.ntotal
        self.index.add(embeddings)
        end = self.index.ntotal
        return list(range(start, end))

    def search(self, query_embedding: np.ndarray, top_k: int) -> Tuple[np.ndarray, np.ndarray]:
        return self.index.search(query_embedding, top_k)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path))

    @classmethod
    def load(cls, path: Path) -> "FaissStore":
        index = faiss.read_index(str(path))
        store = cls(index.d)
        store.index = index
        return store
