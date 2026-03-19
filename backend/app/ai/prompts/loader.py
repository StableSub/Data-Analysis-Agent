"""
Helpers for loading prompt templates from disk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal

from .registry import PROMPT_REGISTRY

PromptRole = Literal["system", "human", "user"]

PROMPTS_BASE_DIR: Final[Path] = Path(__file__).resolve().parent
PROMPT_FILE_NAMES: Final[dict[PromptRole, str]] = {
    "system": "system.md",
    "human": "human.md",
    "user": "user.md",
}


def load_prompt(prompt_dir: str, role: PromptRole) -> str:
    """
    Load a prompt template file by relative prompt directory and role.
    """
    file_name = PROMPT_FILE_NAMES[role]
    prompt_path = PROMPTS_BASE_DIR / prompt_dir / file_name

    if not prompt_path.exists() or not prompt_path.is_file():
        raise FileNotFoundError(
            f"Prompt file not found for dir='{prompt_dir}', role='{role}': {prompt_path}"
        )

    return prompt_path.read_text(encoding="utf-8").strip()


def load_prompt_by_key(prompt_key: str, role: PromptRole) -> str:
    """
    Load a prompt template file using a registered prompt key.
    """
    meta = PROMPT_REGISTRY.get(prompt_key)
    if meta is None:
        raise KeyError(f"Unknown prompt key: {prompt_key}")

    return load_prompt(meta["dir"], role)

