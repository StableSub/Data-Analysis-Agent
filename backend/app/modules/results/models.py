from sqlalchemy import Column, DateTime, JSON, LargeBinary, String, Text
from sqlalchemy.sql import func

from ...core.db import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, index=True)
    data_json = Column(JSON, nullable=True)
    analysis_plan_json = Column(JSON, nullable=True)
    generated_code = Column(Text, nullable=True)
    used_columns = Column(JSON, nullable=True)
    result_json = Column(JSON, nullable=True)
    table = Column(JSON, nullable=True)
    chart_data = Column(JSON, nullable=True)
    execution_status = Column(String(32), nullable=True)
    error_stage = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
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
