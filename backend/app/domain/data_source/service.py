import os
import uuid
from pathlib import Path
from typing import IO, Any, Dict, List, Optional, Tuple

import pandas as pd

from .models import Dataset
from .repository import DataSourceRepository
from .schemas import ManualVizRequest


class DataSourceService:
    def __init__(self, repository: DataSourceRepository, storage_dir: Path) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _persist_file(self, file_stream: IO[bytes], filename: str) -> Tuple[Path, int]:
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

    def _read_csv(
        self,
        dataset: Dataset,
        *,
        nrows: Optional[int] = None,
        usecols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("파일이 존재하지 않습니다.")

        return pd.read_csv(
            file_path,
            encoding="utf-8",
            sep=",",
            nrows=nrows,
            usecols=usecols,
        )

    def upload_dataset(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: Optional[str] = None,
    ) -> Dataset:
        storage_path, size = self._persist_file(file_stream, original_filename)

        dataset = Dataset(
            filename=display_name or original_filename,
            storage_path=str(storage_path),
            filesize=size,
        )
        return self.repository.create(dataset)

    def list_datasets(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dataset]:
        datasets = self.repository.list_all()
        end = skip + limit if limit is not None else None
        return datasets[skip:end]

    def get_dataset_detail(self, dataset_id: int) -> Optional[Dict[str, Dataset]]:
        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            return None
        return {"dataset": dataset}

    def delete_dataset(self, source_id: str) -> Dict[str, Any]:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return {
                "success": False,
                "deleted_file": None,
                "message": "데이터셋을 찾을 수 없습니다.",
            }

        deleted_info = {
            "source_id": dataset.source_id,
            "filename": dataset.filename,
            "storage_path": dataset.storage_path,
        }

        file_path = Path(dataset.storage_path)
        if file_path.exists() and file_path.is_file():
            try:
                os.remove(file_path)
            except OSError:
                pass

        self.repository.delete(dataset)
        return {
            "success": True,
            "deleted_file": deleted_info,
            "message": "데이터셋이 성공적으로 삭제되었습니다.",
        }

    def get_dataset_sample(self, source_id: str, n_rows: int = 5) -> Optional[Dict[str, Any]]:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return None

        try:
            df = self._read_csv(dataset, nrows=n_rows)
        except Exception:
            return None

        return {
            "source_id": source_id,
            "columns": df.columns.tolist(),
            "rows": df.where(pd.notnull(df), None).to_dict(orient="records"),
        }

    def get_manual_viz_data(self, request: ManualVizRequest) -> Dict[str, Any]:
        dataset = self.repository.get_by_source_id(request.source_id)
        if not dataset:
            return {"error": "NOT_FOUND", "message": "데이터셋을 찾을 수 없습니다."}

        requested_cols = [request.columns.x, request.columns.y]
        if request.columns.color:
            requested_cols.append(request.columns.color)
        if request.columns.group:
            requested_cols.append(request.columns.group)
        requested_cols = list(dict.fromkeys(requested_cols))

        try:
            df = self._read_csv(
                dataset,
                nrows=request.limit,
                usecols=requested_cols,
            )
        except FileNotFoundError:
            return {"error": "FILE_NOT_FOUND", "message": "파일이 존재하지 않습니다."}
        except ValueError as e:
            return {"error": "INVALID_COLUMN", "message": str(e)}
        except Exception as e:
            return {"error": "INTERNAL_ERROR", "message": f"데이터 처리 중 오류: {e}"}

        if df.empty:
            return {"error": "NO_DATA", "message": "조회된 데이터가 없습니다."}

        return {
            "chart_type": request.chart_type,
            "data": df.where(pd.notnull(df), None).to_dict(orient="records"),
        }
