from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage

load_dotenv()


class LLMGateway:
    def __init__(self, *, default_model: str = "gpt-5-nano") -> None:
        self.default_model = default_model

    def invoke(
        self,
        *,
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> Any:
        model_name = model_id or self.default_model
        llm = init_chat_model(model_name, temperature=temperature)
        return llm.invoke(list(messages))

    async def stream(
        self,
        *,
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ):
        model_name = model_id or self.default_model
        llm = init_chat_model(model_name, temperature=temperature)
        async for chunk in llm.astream(list(messages)):
            yield chunk
