from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel


class DatasetBase(BaseModel):
    name: str


class DatasetCreate(DatasetBase):
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    extra_metadata: Optional[Dict[str, str]] = None


class DatasetRead(DatasetBase):
    id: int
    original_filename: str
    storage_path: str
    encoding: Optional[str]
    delimiter: Optional[str]
    size_bytes: Optional[int]
    extra_metadata: Optional[Dict[str, str]]
    uploaded_at: datetime

    class Config:
        orm_mode = True


class DatasetDeleteResponse(BaseModel):
    id: int
    deleted: bool
