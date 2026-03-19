from __future__ import annotations

from typing import Any, Dict


def resolve_target_source_id(state: Dict[str, Any]) -> str | None:
    preprocess_result = state.get("preprocess_result")
    if isinstance(preprocess_result, dict) and preprocess_result.get("status") == "applied":
        output_source_id = preprocess_result.get("output_source_id")
        if isinstance(output_source_id, str) and output_source_id.strip():
            return output_source_id.strip()

    rag_result = state.get("rag_result")
    if isinstance(rag_result, dict):
        rag_source_id = rag_result.get("source_id")
        if isinstance(rag_source_id, str) and rag_source_id.strip():
            return rag_source_id.strip()

    source_id = state.get("source_id")
    if isinstance(source_id, str) and source_id.strip():
        return source_id.strip()
    return None
