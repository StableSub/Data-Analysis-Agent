from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from ...core.db import get_db
from .repository import DataSourceRepository
from .service import DataSourceService, DatasetReader, DatasetStorage


def _datasets_storage_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "storage" / "datasets"


def build_data_source_repository(db: Session) -> DataSourceRepository:
    return DataSourceRepository(db)


def get_data_source_repository(db: Session = Depends(get_db)) -> DataSourceRepository:
    return build_data_source_repository(db)


def build_dataset_storage() -> DatasetStorage:
    return DatasetStorage(_datasets_storage_dir())


def get_dataset_storage() -> DatasetStorage:
    return build_dataset_storage()


def build_dataset_reader() -> DatasetReader:
    return DatasetReader()


def get_dataset_reader() -> DatasetReader:
    return build_dataset_reader()


def build_data_source_service(
    *,
    repository: DataSourceRepository,
    storage: DatasetStorage,
    reader: DatasetReader,
) -> DataSourceService:
    return DataSourceService(
        repository=repository,
        storage=storage,
        reader=reader,
    )


def get_data_source_service(
    repository: DataSourceRepository = Depends(get_data_source_repository),
    storage: DatasetStorage = Depends(get_dataset_storage),
    reader: DatasetReader = Depends(get_dataset_reader),
) -> DataSourceService:
    return build_data_source_service(
        repository=repository,
        storage=storage,
        reader=reader,
    )
