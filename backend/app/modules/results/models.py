from sqlalchemy import Column, DateTime, JSON, LargeBinary, String
from sqlalchemy.sql import func

from ...core.db import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, index=True)
    data_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChartResult(Base):
    __tablename__ = "chart_results"

    id = Column(String(36), primary_key=True, index=True)
    image_data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ViewSnapshot(Base):
    __tablename__ = "view_snapshots"

    token = Column(String(64), primary_key=True, index=True)
    data_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
