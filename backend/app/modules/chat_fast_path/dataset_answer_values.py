from __future__ import annotations

from collections.abc import Mapping
from typing import TypeGuard


def as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def as_float(value: object) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    text = str(value or "").strip()
    if text.replace(".", "", 1).isdigit():
        return float(text)
    return 0.0


def as_text_list(value: object) -> list[str]:
    if not _is_object_list(value):
        return []
    return [text for item in value if (text := as_text(item))]


def as_mapping(value: object) -> Mapping[str, object]:
    if _is_text_key_mapping(value):
        return value
    return {}


def as_records(value: object) -> list[Mapping[str, object]]:
    if not _is_object_list(value):
        return []
    return [as_mapping(item) for item in value if _is_text_key_mapping(item)]


def format_value(value: object) -> str:
    text = as_text(value)
    if not text:
        return ""
    return text.replace("\n", " ")[:80]


def _is_object_list(value: object) -> TypeGuard[list[object]]:
    return isinstance(value, list)


def _is_text_key_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    return isinstance(value, Mapping)
