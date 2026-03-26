from sqlalchemy import Column, DateTime, JSON, String
from sqlalchemy.sql import func

from ...core.db import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, index=True)
    data_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
