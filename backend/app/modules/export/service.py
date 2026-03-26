import io
import json
from datetime import datetime

import pandas as pd

from ..results.repository import ResultsRepository


class ExportService:
    """내보내기 원본 바이트 생성만 담당한다."""

    def __init__(self, results_repository: ResultsRepository) -> None:
        self.results_repository = results_repository

    def export_csv(self, result_id: str) -> tuple[io.BytesIO | None, str | None]:
        data = self.results_repository.get_analysis_result_data(result_id)
        if data is None:
            return None, None
        if isinstance(data, str):
            data = json.loads(data)

        df = pd.DataFrame(data)
        byte_stream = io.BytesIO()
        byte_stream.write(b"\xef\xbb\xbf")
        df.to_csv(byte_stream, index=False, encoding="utf-8", mode="wb")
        byte_stream.seek(0)
        filename = f"result_{datetime.now().strftime('%Y%m%d')}.csv"
        return byte_stream, filename
