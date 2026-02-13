import io
import json
from datetime import datetime
from typing import Tuple

import pandas as pd
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session


class ExportService:
    """분석 결과를 CSV로 내보내는 최소 서비스."""

    def __init__(self, db: Session):
        self.db = db

    def _get_data_from_db(self, result_id: str) -> pd.DataFrame | None:
        """analysis_results 테이블에서 result_id를 조회해 DataFrame으로 변환한다."""
        query = text("SELECT data_json FROM analysis_results WHERE id = :id")
        row = self.db.execute(query, {"id": result_id}).fetchone()
        if not row or not row[0]:
            return None

        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        return pd.DataFrame(data)

    def export_csv(self, result_id: str) -> Tuple[StreamingResponse | None, str]:
        """CSV 스트리밍 응답을 생성한다."""
        df = self._get_data_from_db(result_id)
        if df is None:
            return None, "NO_RESULT"

        byte_stream = io.BytesIO()
        byte_stream.write(b"\xef\xbb\xbf")
        df.to_csv(byte_stream, index=False, encoding="utf-8", mode="wb")
        byte_stream.seek(0)

        filename = f"result_{datetime.now().strftime('%Y%m%d')}.csv"
        response = StreamingResponse(byte_stream, media_type="text/csv")
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response, "SUCCESS"
