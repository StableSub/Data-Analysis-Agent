import uuid
from pathlib import Path
from typing import IO, Any, Optional

from .models import Guideline
from .repository import GuidelineRepository

ALLOWED_GUIDELINE_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
}


class GuidelineService:
    """지침서 파일 저장/조회/활성화/삭제를 담당한다."""

    def __init__(self, repository: GuidelineRepository, storage_dir: Path) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_guideline_pdf(*, filename: str, content_type: str | None = None) -> None:
        normalized_filename = (filename or "").strip()
        if not normalized_filename:
            raise ValueError("파일명이 비어 있습니다.")

        if not normalized_filename.lower().endswith(".pdf"):
            raise ValueError("지침서는 PDF 파일만 업로드할 수 있습니다.")

        normalized_content_type = (content_type or "").lower()
        if normalized_content_type and normalized_content_type not in ALLOWED_GUIDELINE_MIME_TYPES:
            raise ValueError("PDF MIME 타입 파일만 업로드할 수 있습니다.")

    def _persist_file(self, file_stream: IO[bytes], filename: str) -> tuple[Path, int]:
        if hasattr(file_stream, "seek"):
            file_stream.seek(0)

        target_path = self.storage_dir / f"{uuid.uuid4().hex}_{filename}"
        size = 0
        with open(target_path, "wb") as target:
            while True:
                chunk = file_stream.read(8192)
                if not chunk:
                    break
                size += len(chunk)
                target.write(chunk)
        return target_path, size

    def upload_guideline(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: Optional[str] = None,
        content_type: str | None = None,
    ) -> Guideline:
        self._validate_guideline_pdf(filename=original_filename, content_type=content_type)
        storage_path, size = self._persist_file(file_stream, original_filename)
        latest = self.repository.get_latest_version(display_name or original_filename)
        next_version = (latest.version + 1) if latest else 1

        guideline = Guideline(
            filename=display_name or original_filename,
            storage_path=str(storage_path),
            filesize=size,
            version=next_version,
            is_active=False,
        )
        return self.repository.create(guideline)

    def list_guidelines(self, skip: int = 0, limit: int = 20) -> tuple[list[Guideline], int]:
        items = self.repository.list_page(skip=skip, limit=limit)
        total = self.repository.count_all()
        return items, total

    def get_active_guideline(self) -> Optional[Guideline]:
        return self.repository.get_active()

    def get_guideline_by_source_id(self, source_id: str) -> Optional[Guideline]:
        return self.repository.get_by_source_id(source_id)

    def activate_guideline(self, source_id: str) -> Optional[Guideline]:
        guideline = self.repository.get_by_source_id(source_id)
        if not guideline:
            return None

        return self.repository.activate(guideline)

    def delete_guideline(self, source_id: str) -> bool:
        guideline = self.repository.get_by_source_id(source_id)
        if not guideline:
            return False

        file_path = Path(guideline.storage_path)
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            raise

        self.repository.delete(guideline)
        return True
