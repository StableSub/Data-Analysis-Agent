import io
import json
import pandas as pd
from datetime import datetime
from typing import Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import StreamingResponse

from backend.app.domain.analysis.models import AnalysisResult, ChartResult 

class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def _get_data_from_db(self, result_id: Optional[str], view_token: Optional[str]) -> Optional[pd.DataFrame]:
        """
        DB에서 분석 결과를 조회하여 DataFrame으로 변환합니다.
        """
        if not result_id and not view_token:
            return None
            
        # 1. result_id로 조회하는 경우
        if result_id:
            
            # Raw SQL로 구현 
            query = text("SELECT data_json FROM analysis_results WHERE id = :id")
            row = self.db.execute(query, {"id": result_id}).fetchone()
            
            if row and row[0]:
                # DB에 저장된 JSON 데이터를 DataFrame으로 변환
                data = row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                return pd.DataFrame(data)

        # 2. view_token (스냅샷)으로 조회하는 경우
        if view_token:
            query = text("SELECT data_json FROM view_snapshots WHERE token = :token")
            row = self.db.execute(query, {"token": view_token}).fetchone()
            
            if row and row[0]:
                data = row[0]
                if isinstance(data, str):
                    data = json.loads(data)
                return pd.DataFrame(data)

        return None

    def _get_chart_image_from_db(self, chart_id: str) -> Optional[bytes]:
        """
        DB에서 차트 이미지(BLOB)를 조회합니다.
        """
        query = text("SELECT image_data FROM chart_results WHERE id = :id")
        row = self.db.execute(query, {"id": chart_id}).fetchone()
        
        if row and row[0]:
            return row[0] # BLOB 데이터 반환
            
        return None

    def export_csv(self, params) -> Tuple[StreamingResponse, str]:
        """
        DB 데이터를 조회하여 CSV 스트리밍 응답 생성
        """
        df = self._get_data_from_db(params.result_id, params.view_token)
        
        if df is None:
            return None, "NO_RESULT"

        if params.columns:
            # 실제 데이터프레임에 존재하는 컬럼만 교집합으로 선택
            valid_cols = [c for c in params.columns if c in df.columns]
            if valid_cols:
                df = df[valid_cols]
        
        if params.limit:
            df = df.head(params.limit)

        # CSV 변환 
        byte_stream = io.BytesIO()
        
        # 엑셀에서 한글 깨짐 방지를 위해 BOM(Byte Order Mark) 추가
        byte_stream.write(b'\xef\xbb\xbf')
        
        df.to_csv(
            byte_stream, 
            index=False, 
            header=params.include_header, 
            encoding='utf-8', 
            mode='wb' 
        )
        byte_stream.seek(0) 

        filename = f"result_{datetime.now().strftime('%Y%m%d')}.csv"

        response = StreamingResponse(
            byte_stream, 
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return response, "SUCCESS"

    def export_chart(self, params) -> Tuple[StreamingResponse, str]:
        """
        DB 이미지를 조회하여 PNG 스트리밍 응답 생성
        """
        image_bytes = self._get_chart_image_from_db(params.chart_id)
        
        if image_bytes is None:
            return None, "NO_RESULT"
            
        byte_stream = io.BytesIO(image_bytes)
        
        filename = f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        response = StreamingResponse(
            byte_stream, 
            media_type="image/png"
        )
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return response, "SUCCESS"