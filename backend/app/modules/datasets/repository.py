from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Dataset


class DatasetRepository:
    """데이터셋 영속화/조회/삭제를 담당하는 저장소 계층."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, dataset: Dataset) -> Dataset:
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def list_page(self, skip: int = 0, limit: int = 20) -> List[Dataset]:
        return (
            self.db.query(Dataset)
            .order_by(Dataset.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_all(self) -> int:
        return self.db.query(Dataset).count()

    def get_by_source_id(self, source_id: str) -> Optional[Dataset]:
        return self.db.query(Dataset).filter(Dataset.source_id == source_id).first()

    def delete(self, dataset: Dataset) -> None:
        self.db.delete(dataset)
        self.db.commit()


# Compatibility alias for modules that still use the older repository name.
DataSourceRepository = DatasetRepository
