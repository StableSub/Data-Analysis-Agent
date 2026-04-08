from __future__ import annotations

from typing import Any, Dict


def resolve_target_source_id(state: Dict[str, Any]) -> str | None:
    # source_id always means the dataset currently selected in the UI.
    # Generated preprocess outputs are tracked separately via preprocess_result.
    source_id = state.get("source_id")
    if isinstance(source_id, str) and source_id.strip():
        return source_id.strip()
    return None
