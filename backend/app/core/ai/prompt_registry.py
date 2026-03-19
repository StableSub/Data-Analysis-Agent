from __future__ import annotations

from typing import Mapping


class PromptRegistry:
    def __init__(self, prompts: Mapping[str, str]) -> None:
        self._prompts = dict(prompts)

    def load_prompt(self, key: str) -> str:
        prompt = self._prompts.get(key)
        if prompt is None:
            raise KeyError(f"Prompt not found: {key}")
        return prompt
