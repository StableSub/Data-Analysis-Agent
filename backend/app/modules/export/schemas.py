from pydantic import BaseModel, Field


class CsvExportParams(BaseModel):
    """CSV 내보내기 요청 파라미터(최소 버전)."""

    result_id: str = Field(..., description="분석 결과 ID")
