"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

from pathlib import Path

from ...ai.agents.builder import AgentBuilder


class AgentClient:
    def __init__(
        self,
        model: str = "gpt-5-nano",
    ) -> None:
        self.model = model
        # 에이전트와 메모리를 초기화 시점에 한 번만 생성하여 유지합니다.
        self.agent = AgentBuilder(model_name=model).build()

    def ask(self, session_id: str | None = None,
            question: str | None = None,
            context: str | None = None) -> str:
        """
        질문과 선택적 추가 컨텍스트를 받아 답변을 생성한다.
        """
        # 저장된 self.agent를 재사용합니다.
        
        if context:
            message = f"{question} 이것은 사용자의 질문 입니다. {context} 이것은 관련된 context 입니다."
        else:
            message = f"{question} 이것은 사용자의 질문 입니다."
            
        # config에 thread_id를 전달하여 대화 흐름을 유지합니다.
        response = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            {"configurable": {"thread_id": session_id}}
        )
        return response["messages"][-1].content

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
            return AgentClient._load_pdf(file_path, max_chars)

        data = file_path.read_text(encoding="utf-8", errors="ignore")
        return data[:max_chars]

    @staticmethod
    def _load_pdf(file_path: Path, max_chars: int) -> str:
        """
        간단한 PDF 텍스트 추출.
        """
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
