from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class LLMGateway:
    def __init__(self, *, default_model: str = "gpt-5-nano") -> None:
        self.default_model = default_model

    def _build_model(
        self,
        *,
        model_id: str | None,
        temperature: float,
    ):
        model_name = model_id or self.default_model
        return init_chat_model(model_name, temperature=temperature)

    def invoke(
        self,
        *,
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> Any:
        llm = self._build_model(model_id=model_id, temperature=temperature)
        return llm.invoke(list(messages))

    async def stream(
        self,
        *,
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ):
        llm = self._build_model(model_id=model_id, temperature=temperature)
        async for chunk in llm.astream(list(messages)):
            yield chunk

    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> Any:
        llm = self._build_model(model_id=model_id, temperature=temperature).with_structured_output(
            schema,
            method="function_calling",
        )
        return llm.invoke(list(messages))
