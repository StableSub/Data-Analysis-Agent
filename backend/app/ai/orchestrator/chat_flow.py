from typing import Iterable, List, Optional

from ..llm.client import LLMClient
from ...domain.chat.models import ChatMessage


class ChatFlowOrchestrator:
    """
    히스토리/추가 컨텍스트를 묶어 LLMClient에 전달하는 오케스트레이터.
    LLM 호출 실패 시 간단한 에코 답변으로 폴백합니다.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def generate_answer(
        self,
        *,
        session_id: int,
        question: str,
        history: Optional[Iterable[ChatMessage]],
        context: str | None = None,
    ) -> str:
        prompt_context = self._build_context(history=history or [], extra_context=context)
        try:
            return self.llm_client.ask(question=question, context=prompt_context)
        except Exception as exc:
            # 키 미설정 등으로 LLM 호출이 실패할 때 폴백
            history_len = len(list(history or []))
            return f"[fallback][session:{session_id}][history:{history_len}] {question}\ncontext: {prompt_context}\nerror: {exc}"

    def _build_context(
        self, *, history: Iterable[ChatMessage], extra_context: str | None
    ) -> str:
        sections: List[str] = []
        if history:
            sections.append("=== HISTORY ===")
            sections.append(self._format_history(history))
        if extra_context:
            sections.append("=== EXTRA CONTEXT ===")
            sections.append(extra_context)
        return "\n\n".join(sections) if sections else "No extra context"

    @staticmethod
    def _format_history(history: Iterable[ChatMessage]) -> str:
        return "\n".join(f"{msg.role}: {msg.content}" for msg in history)
