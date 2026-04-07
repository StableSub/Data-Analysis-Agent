from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from .repository import DatasetRepository
from .service import DatasetReader, DatasetService, DatasetStorage


def _datasets_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "datasets"


def build_dataset_repository(db: Session) -> DatasetRepository:
    return DatasetRepository(db)


def get_dataset_repository(db: Session = Depends(get_db)) -> DatasetRepository:
    return build_dataset_repository(db)


def build_data_source_repository(db: Session) -> DatasetRepository:
    return build_dataset_repository(db)


def get_data_source_repository(db: Session = Depends(get_db)) -> DatasetRepository:
    return build_data_source_repository(db)


def build_dataset_storage() -> DatasetStorage:
    return DatasetStorage(_datasets_storage_dir())


def get_dataset_storage() -> DatasetStorage:
    return build_dataset_storage()


def build_dataset_reader() -> DatasetReader:
    return DatasetReader()


def get_dataset_reader() -> DatasetReader:
    return build_dataset_reader()


def build_dataset_service(
    *,
    repository: DatasetRepository,
    storage: DatasetStorage,
    reader: DatasetReader,
) -> DatasetService:
    return DatasetService(
        repository=repository,
        storage=storage,
        reader=reader,
    )


def get_dataset_service(
    repository: DatasetRepository = Depends(get_dataset_repository),
    storage: DatasetStorage = Depends(get_dataset_storage),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> DatasetService:
    return build_dataset_service(
        repository=repository,
        storage=storage,
        reader=reader,
    )
