"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .model_selector import LLMPresetName, get_llm


class LLMClient:
    """기본 시스템 프롬프트 + LLM + 출력 파서를 묶은 매우 단순한 헬퍼."""

    def __init__(
        self,
        preset: LLMPresetName | None = None,
        system_prompt: str = "데이터 분석을 도와주는 AI 어시스턴트",
    ) -> None:
        self.preset = preset
        self.system_prompt = system_prompt

    def _chain(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("human", "{question}\n\n추가 정보:\n{context}"),
            ]
        )
        llm = get_llm(self.preset)
        return prompt | llm | StrOutputParser()

    def ask(self, question: str, context: str | None = None) -> str:
        """질문과 선택적 추가 컨텍스트(예: 파일 내용)를 받아 답변을 생성한다."""
        chain = self._chain()
        return chain.invoke({"question": question, "context": context or "없음"})

    @staticmethod
    def load_text_from_file(path: str, max_chars: int = 4000) -> str:
        """
        텍스트 또는 PDF 파일을 읽어 제한 길이만큼 잘라 반환한다.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return LLMClient._load_pdf(file_path, max_chars)

        data = file_path.read_text(encoding="utf-8", errors="ignore")
        return data[:max_chars]

    @staticmethod
    def _load_pdf(file_path: Path, max_chars: int) -> str:
        """간단한 PDF 텍스트 추출 (pypdf 의존)."""
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "PDF 파일을 처리하려면 'pypdf' 패키지가 필요합니다. pip install pypdf 로 설치하세요."
            ) from exc

        reader = PdfReader(str(file_path))
        chunks: list[str] = []
        total_len = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                available = max_chars - total_len
                if available <= 0:
                    break
                snippet = text[:available]
                chunks.append(snippet)
                total_len += len(snippet)
            if total_len >= max_chars:
                break
        return "\n".join(chunks)
