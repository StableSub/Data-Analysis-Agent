import uuid
from pathlib import Path
from typing import IO, Any, Optional

from .models import Guideline
from .repository import GuidelineRepository


class GuidelineService:
    """지침서 파일 저장/조회/활성화/삭제를 담당한다."""

    def __init__(self, repository: GuidelineRepository, storage_dir: Path) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

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
    ) -> Guideline:
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

    def list_guidelines(self, skip: int = 0, limit: int = 20) -> list[Guideline]:
        guidelines = self.repository.list_all()
        end = skip + limit if limit is not None else None
        return guidelines[skip:end]

    def get_active_guideline(self) -> Guideline | None:
        return self.repository.get_active()

    def activate_guideline(self, source_id: str) -> dict[str, Any]:
        guideline = self.repository.get_by_source_id(source_id)
        if not guideline:
            return {
                "success": False,
                "message": "지침서를 찾을 수 없습니다.",
            }

        activated = self.repository.activate(guideline)
        return {
            "success": True,
            "guideline": activated,
            "message": "지침서가 활성화되었습니다.",
        }

    def delete_guideline(self, source_id: str) -> dict[str, Any]:
        guideline = self.repository.get_by_source_id(source_id)
        if not guideline:
            return {
                "success": False,
                "deleted_file": None,
                "message": "지침서를 찾을 수 없습니다.",
            }

        deleted_info = {
            "source_id": guideline.source_id,
            "guideline_id": guideline.guideline_id,
            "filename": guideline.filename,
            "storage_path": guideline.storage_path,
            "is_active": guideline.is_active,
        }

        file_path = Path(guideline.storage_path)
        try:
            file_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            raise

        self.repository.delete(guideline)
        return {
            "success": True,
            "deleted_file": deleted_info,
            "message": "지침서가 성공적으로 삭제되었습니다.",
        }

