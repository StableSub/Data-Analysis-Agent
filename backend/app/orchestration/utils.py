from __future__ import annotations

from typing import Any, Dict


def resolve_target_source_id(state: Dict[str, Any]) -> str | None:
    preprocess_result = state.get("preprocess_result")
    source_id = state.get("source_id")

    if isinstance(preprocess_result, dict) and preprocess_result.get("status") == "applied":
        output_source_id = preprocess_result.get("output_source_id")
        input_source_id = preprocess_result.get("input_source_id")
        if isinstance(output_source_id, str) and output_source_id.strip():
            if not isinstance(source_id, str) or not source_id.strip():
                return output_source_id.strip()
            if isinstance(input_source_id, str) and source_id.strip() == input_source_id.strip():
                return output_source_id.strip()

    if isinstance(source_id, str) and source_id.strip():
        return source_id.strip()
    return None
