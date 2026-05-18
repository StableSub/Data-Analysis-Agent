from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
EVALUATION_DIR = REPO_ROOT / "evaluation"
CASES_DIR = EVALUATION_DIR / "cases"
RAW_DIR = EVALUATION_DIR / "raw"


def dataset_path(dataset_name: str) -> Path:
    return RAW_DIR / dataset_name


def require_dataset_path(dataset_name: str) -> Path:
    path = dataset_path(dataset_name)
    if not path.exists():
        raise FileNotFoundError(f"evaluation raw dataset is missing: {path}")
    return path


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            if not isinstance(payload, dict):
                raise AssertionError(f"{path}:{line_number} is not a JSON object")
            cases.append(payload)
    return cases


def load_case_file(filename: str) -> list[dict[str, Any]]:
    return load_jsonl(CASES_DIR / filename)


def load_all_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(CASES_DIR.glob("*.jsonl")):
        cases.extend(load_jsonl(path))
    return cases
