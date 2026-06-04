from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ..datasets.models import DATASET_FILENAME_MAX_LENGTH, DATASET_SOURCE_ID_MAX_LENGTH
from ..datasets.repository import DatasetRepository

_NON_WORD_PATTERN: Final = re.compile(r"\W+", flags=re.UNICODE)
_UNDERSCORE_PATTERN: Final = re.compile(r"_+")
_PREPROCESS_SUFFIX_PATTERN: Final = re.compile(r"_전처리_\d+$")
_FALLBACK_DATASET_NAME: Final = "dataset"
_CSV_EXTENSION: Final = ".csv"
_FILESYSTEM_NAME_MAX_BYTES: Final = 255


@dataclass(frozen=True, slots=True)
class PreprocessOutputTarget:
    source_id: str
    filename: str
    storage_path: Path


def normalize_preprocess_source_stem(filename: str) -> str:
    stem = unicodedata.normalize("NFKC", Path(filename).stem).strip()
    candidate = _NON_WORD_PATTERN.sub("_", stem)
    candidate = _UNDERSCORE_PATTERN.sub("_", candidate).strip("_")
    candidate = _PREPROCESS_SUFFIX_PATTERN.sub("", candidate)
    return candidate or _FALLBACK_DATASET_NAME


def _truncate_utf8(text: str, max_bytes: int) -> str:
    result: list[str] = []
    used_bytes = 0
    for char in text:
        char_bytes = len(char.encode("utf-8"))
        if used_bytes + char_bytes > max_bytes:
            break
        result.append(char)
        used_bytes += char_bytes
    return "".join(result)


def _build_source_id(source_stem: str, suffix: int) -> str:
    suffix_text = f"_전처리_{suffix}"
    max_source_id_length = min(
        DATASET_SOURCE_ID_MAX_LENGTH,
        DATASET_FILENAME_MAX_LENGTH - len(_CSV_EXTENSION),
    )
    max_source_id_bytes = _FILESYSTEM_NAME_MAX_BYTES - len(_CSV_EXTENSION.encode("utf-8"))
    max_stem_length = max_source_id_length - len(suffix_text)
    max_stem_bytes = max_source_id_bytes - len(suffix_text.encode("utf-8"))
    capped_stem = _truncate_utf8(
        source_stem[:max_stem_length],
        max_stem_bytes,
    ).strip("_")
    capped_stem = capped_stem or _FALLBACK_DATASET_NAME
    return f"{capped_stem}{suffix_text}"


def build_preprocess_output_target(
    *,
    input_filename: str,
    input_storage_path: str,
    repository: DatasetRepository,
) -> PreprocessOutputTarget:
    source_stem = normalize_preprocess_source_stem(input_filename)
    output_dir = Path(input_storage_path).parent
    suffix = 1

    while True:
        source_id = _build_source_id(source_stem, suffix)
        filename = f"{source_id}{_CSV_EXTENSION}"
        storage_path = output_dir / filename
        if repository.get_by_source_id(source_id) is None and not storage_path.exists():
            return PreprocessOutputTarget(
                source_id=source_id,
                filename=filename,
                storage_path=storage_path,
            )
        suffix += 1
