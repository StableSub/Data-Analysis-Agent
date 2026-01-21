# 오류 처리
class RagError(RuntimeError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class RagNotIndexedError(RagError):
    def __init__(self, message: str = "NOT_INDEXED") -> None:
        super().__init__(message, code="NOT_INDEXED")


class RagEmbeddingError(RagError):
    def __init__(self, message: str = "EMBEDDING_ERROR") -> None:
        super().__init__(message, code="EMBEDDING_ERROR")


class RagSearchError(RagError):
    def __init__(self, message: str = "SEARCH_ERROR") -> None:
        super().__init__(message, code="SEARCH_ERROR")
