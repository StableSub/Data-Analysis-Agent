"""
LLMClient는 선택된 프리셋으로 LangChain 체인을 구성해 간단한 질의를 처리한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...core.db import SessionLocal
from .builder import WorkflowBuilder


class AgentClient:
    def __init__(
        self,
        model: str = "gpt-5-nano",
    ) -> None:
        self.default_model = model

    def ask(self, session_id: str | None = None,
            question: str | None = None,
            context: str | None = None,
            dataset: Any | None = None,
            model_id: str | None = None) -> str:
        """
        질문과 선택적 추가 컨텍스트를 받아 답변을 생성한다.
        """
        dataset_context = self._build_dataset_context(dataset) if dataset is not None else ""
        merged_context_parts: list[str] = []
        if dataset_context:
            merged_context_parts.append(dataset_context)
        if context:
            merged_context_parts.append(context)
        merged_context = "\n\n".join(merged_context_parts).strip()
        question_text = (question or "").strip()
        if not question_text:
            return "질문을 입력해 주세요."

        if merged_context:
            message = f"{question_text}\n\ncontext:\n{merged_context}"
        else:
            message = question_text

        state = {
            "user_input": message,
            "session_id": str(session_id or ""),
            "model_id": model_id or self.default_model,
            "user_context": {"context": merged_context} if merged_context else {},
            "dataset_id": getattr(dataset, "id", None) if dataset is not None else None,
            "source_id": getattr(dataset, "source_id", None) if dataset is not None else None,
        }

        db = SessionLocal()
        try:
            workflow = WorkflowBuilder(
                db=db,
                model_name=self.default_model,
            ).build()
            result_state = workflow.invoke(state)
        finally:
            db.close()

        output = result_state.get("output") or {}
        content = output.get("content")
        if isinstance(content, str) and content:
            return content
        return str(output) if output else "No output"

    def _build_dataset_context(self, dataset: Any, max_rows: int = 20) -> str:
        """
        Dataset 객체에서 파일 내용을 읽어 LLM에 전달할 축약 컨텍스트를 만든다.
        """
        storage_path = getattr(dataset, "storage_path", None)
        filename = getattr(dataset, "filename", "dataset")
        if not storage_path:
            return ""

        file_path = Path(storage_path)
        if not file_path.exists() or not file_path.is_file():
            return ""

        try:
            if file_path.suffix.lower() == ".csv":
                import pandas as pd

                df = pd.read_csv(file_path, nrows=max_rows)
                preview_records = df.where(df.notnull(), None).to_dict(orient="records")
                return (
                    f"dataset filename={filename}\n"
                    f"columns={json.dumps(df.columns.tolist(), ensure_ascii=False)}\n"
                    f"preview_rows={json.dumps(preview_records, ensure_ascii=False)}"
                )

            raw_text = self.load_text_from_file(str(file_path), max_chars=4000)
            return f"dataset filename={filename}\ncontent_preview={raw_text}"
        except Exception:
            return ""

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
