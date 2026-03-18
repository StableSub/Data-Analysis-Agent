"""
Prompt rendering helpers built on top of the prompt registry and loader.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .loader import PromptRole, load_prompt_by_key
from .registry import PROMPT_REGISTRY


def _validate_prompt_key(prompt_key: str) -> None:
    if prompt_key not in PROMPT_REGISTRY:
        raise KeyError(f"Unknown prompt key: {prompt_key}")


def _validate_required_vars(prompt_key: str, vars: dict[str, Any]) -> None:
    required_vars = PROMPT_REGISTRY[prompt_key]["required_vars"]
    missing_vars = [name for name in required_vars if name not in vars]
    if missing_vars:
        missing_text = ", ".join(missing_vars)
        raise ValueError(f"Missing required vars for '{prompt_key}': {missing_text}")


def _render_role_prompt(prompt_key: str, role: PromptRole, **vars: Any) -> str:
    template = load_prompt_by_key(prompt_key, role)
    return template.format(**vars)


def build_structured_prompt(prompt_key: str, **vars: Any) -> tuple[str, str]:
    """
    Build `(system_prompt, human_prompt)` for prompts that use system/human files.
    """
    _validate_prompt_key(prompt_key)
    _validate_required_vars(prompt_key, vars)

    system_prompt = _render_role_prompt(prompt_key, "system", **vars)
    human_prompt = _render_role_prompt(prompt_key, "human", **vars)
    return system_prompt, human_prompt


def build_messages(prompt_key: str, **vars: Any) -> list[SystemMessage | HumanMessage]:
    """
    Build LangChain messages from the available prompt role files for a prompt key.
    """
    _validate_prompt_key(prompt_key)
    _validate_required_vars(prompt_key, vars)

    messages: list[SystemMessage | HumanMessage] = []

    try:
        system_prompt = _render_role_prompt(prompt_key, "system", **vars)
    except FileNotFoundError:
        system_prompt = ""
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))

    try:
        human_prompt = _render_role_prompt(prompt_key, "human", **vars)
    except FileNotFoundError:
        human_prompt = ""
    if human_prompt:
        messages.append(HumanMessage(content=human_prompt))

    try:
        user_prompt = _render_role_prompt(prompt_key, "user", **vars)
    except FileNotFoundError:
        user_prompt = ""
    if user_prompt:
        messages.append(HumanMessage(content=user_prompt))

    if not messages:
        raise ValueError(f"No prompt files found for '{prompt_key}'")

    return messages

