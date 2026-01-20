from __future__ import annotations

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class E5Embedder:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.embedding_dim = self._model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        prefixed = [f"passage: {text}" for text in texts]
        embeddings = self._model.encode(
            prefixed,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.astype("float32")

    def embed_query(self, query: str) -> np.ndarray:
        prefixed = [f"query: {query}"]
        embeddings = self._model.encode(
            prefixed,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.astype("float32")
