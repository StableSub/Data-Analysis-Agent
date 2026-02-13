from typing import List, Optional

from sqlalchemy.orm import Session

from .models import Dataset


class DataSourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dataset: Dataset) -> Dataset:
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def list_all(self) -> List[Dataset]:
        return self.db.query(Dataset).order_by(Dataset.id.desc()).all()

    def get_by_id(self, dataset_id: int) -> Optional[Dataset]:
        return self.db.query(Dataset).filter(Dataset.id == dataset_id).first()

    def get_by_source_id(self, source_id: str) -> Optional[Dataset]:
        return self.db.query(Dataset).filter(Dataset.source_id == source_id).first()

    def delete(self, dataset: Dataset) -> None:
        self.db.delete(dataset)
        self.db.commit()
