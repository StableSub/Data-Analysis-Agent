from __future__ import annotations

from collections.abc import Mapping
from typing import Any


FAST_PATH_CONTEXT_FIELDS = {
    "column_aliases",
    "column_value_samples",
}
FAST_PATH_BULK_CONTEXT_FIELDS = {
    "column_value_samples",
}


def trim_fast_path_context_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    prompt_payload = dict(payload)
    for field in FAST_PATH_CONTEXT_FIELDS:
        prompt_payload.pop(field, None)
    return prompt_payload


def trim_fast_path_bulk_context_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    prompt_payload = dict(payload)
    for field in FAST_PATH_BULK_CONTEXT_FIELDS:
        prompt_payload.pop(field, None)
    return prompt_payload


def trim_merged_context_fast_path_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    prompt_payload = dict(payload)
    dataset_context = prompt_payload.get("dataset_context")
    if isinstance(dataset_context, Mapping):
        prompt_payload["dataset_context"] = trim_fast_path_context_fields(dataset_context)
    return prompt_payload
