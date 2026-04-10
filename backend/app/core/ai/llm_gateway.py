from __future__ import annotations

from collections.abc import Sequence
import inspect
from time import perf_counter
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from ..trace_logging import get_trace_context, log_trace


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
        started_at = perf_counter()
        llm = self._build_model(model_id=model_id, temperature=temperature)
        result = llm.invoke(list(messages))
        self._log_call(
            call_type="invoke",
            model_id=model_id,
            messages=messages,
            duration_ms=(perf_counter() - started_at) * 1000,
            response=result,
        )
        return result

    async def stream(
        self,
        *,
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ):
        started_at = perf_counter()
        llm = self._build_model(model_id=model_id, temperature=temperature)
        chunks: list[str] = []
        async for chunk in llm.astream(list(messages)):
            chunks.append(self._extract_response_text(chunk))
            yield chunk
        self._log_call(
            call_type="stream",
            model_id=model_id,
            messages=messages,
            duration_ms=(perf_counter() - started_at) * 1000,
            response="".join(chunks),
        )

    def invoke_structured(
        self,
        *,
        schema: type[BaseModel],
        messages: Sequence[BaseMessage],
        model_id: str | None = None,
        temperature: float = 0,
    ) -> Any:
        started_at = perf_counter()
        llm = self._build_model(model_id=model_id, temperature=temperature).with_structured_output(
            schema,
            method="function_calling",
        )
        result = llm.invoke(list(messages))
        self._log_call(
            call_type="invoke_structured",
            model_id=model_id,
            messages=messages,
            duration_ms=(perf_counter() - started_at) * 1000,
            response=result,
            schema_name=schema.__name__,
        )
        return result

    def _log_call(
        self,
        *,
        call_type: str,
        model_id: str | None,
        messages: Sequence[BaseMessage],
        duration_ms: float,
        response: Any,
        schema_name: str | None = None,
    ) -> None:
        context = get_trace_context()
        log_trace(
            layer="llm",
            event=call_type,
            payload={
                "trace_id": context["trace_id"],
                "model_id": model_id or self.default_model,
                "call_type": call_type,
                "schema_name": schema_name,
                "caller": self._resolve_caller(),
                "message_summary": self._summarize_messages(messages),
                "duration_ms": round(duration_ms, 2),
                "response_summary": self._summarize_response(response),
            },
        )

    @staticmethod
    def _resolve_caller() -> str:
        frame = inspect.currentframe()
        if frame is None:
            return ""

        gateway_file = __file__
        current = frame.f_back
        while current is not None:
            if current.f_code.co_filename != gateway_file:
                module = current.f_globals.get("__name__", "")
                function = current.f_code.co_name
                return f"{module}.{function}".strip(".")
            current = current.f_back
        return ""

    @staticmethod
    def _summarize_messages(messages: Sequence[BaseMessage]) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for message in messages:
            content = LLMGateway._extract_response_text(message)
            limit = 300 if getattr(message, "type", "") == "system" else 1000
            summaries.append(
                {
                    "role": getattr(message, "type", ""),
                    "length": len(content),
                    "preview": content[:limit],
                }
            )
        return summaries

    @staticmethod
    def _summarize_response(response: Any) -> Any:
        if hasattr(response, "model_dump") and callable(response.model_dump):
            return response.model_dump()

        content = LLMGateway._extract_response_text(response)
        if content:
            return {
                "length": len(content),
                "preview": content[:1000],
            }

        if isinstance(response, dict):
            return response

        return str(response)

    @staticmethod
    def _extract_response_text(value: Any) -> str:
        if isinstance(value, str):
            return value

        if hasattr(value, "content"):
            content = getattr(value, "content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts: list[str] = []
                for item in content:
                    if isinstance(item, str):
                        parts.append(item)
                    elif isinstance(item, dict):
                        text = item.get("text")
                        if isinstance(text, str):
                            parts.append(text)
                return "".join(parts)

        return ""
