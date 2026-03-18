from pathlib import Path
from typing import List, Optional

import pandas as pd


class DatasetReader:
    """CSV 읽기 책임만 담당한다."""

    def read_csv(
        self,
        storage_path: str,
        *,
        nrows: Optional[int] = None,
        usecols: Optional[List[str]] = None,
        encoding: str = "utf-8",
    ) -> pd.DataFrame:
        file_path = Path(storage_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError("파일이 존재하지 않습니다.")

        return pd.read_csv(
            file_path,
            encoding=encoding,
            sep=",",
            nrows=nrows,
            usecols=usecols,
        )
