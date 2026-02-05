import json
import os
import re
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.domain.data_source.repository import DatasetVersionRepository
from backend.app.domain.preprocess.schemas import (
    PreprocessOperation,
    PreprocessPreviewResponse,
    ColumnPreview,
    PreprocessApplyResponse,
)
from backend.app.domain.data_source.models import Dataset

# 파생 변수 생성 시 사용할 수 있는 안전한 표현 정규식 
_SAFE_EXPR_RE = re.compile(r"^[0-9a-zA-Z_+\-*/%().\s<>=!&|]+$")


class PreprocessService:
    def __init__(self, db: Session):
        self.db = db
        self.versions = DatasetVersionRepository(db)

    # --- public ---
    def preview(self, dataset_id: int, version_id: Optional[int]) -> PreprocessPreviewResponse:
        """
        데이터셋의 특정 버전 미리보기
        컬럼별 메타데이터와 상위 20개 샘플 행 반환
        """
        ds, file_path, resolved_version_id = self._resolve_dataset_file(dataset_id, version_id)
        df = self._read_dataframe(file_path)

        cols = [
            ColumnPreview(
                name=str(c),
                dtype=str(df[c].dtype),
                missing=int(df[c].isna().sum()),
            )
            for c in df.columns
        ]
        sample = df.head(20).where(pd.notnull(df), None).to_dict(orient="records")
        return PreprocessPreviewResponse(
            dataset_id=dataset_id,
            version_id=resolved_version_id,
            columns=cols,
            sample_rows=sample,
        )

    def apply(
        self,
        dataset_id: int,
        base_version_id: Optional[int],
        operations: List[PreprocessOperation],
        created_by: Optional[str],
        note: Optional[str],
    ) -> PreprocessApplyResponse:
        """
        전처리 작업 적용 후 새로운 버전 생성
        """
        ds, base_file_path, resolved_base_version_id = self._resolve_dataset_file(dataset_id, base_version_id)
        df = self._read_dataframe(base_file_path)

        # 전처리 연산 수행
        df2 = self._apply_operations(df, operations)

        out_path = self._make_versioned_path(ds, self.versions.next_version_no(dataset_id))
        self._write_dataframe(df2, out_path)

        ops_json = json.dumps([op.model_dump() for op in operations], ensure_ascii=False)

        v = self.versions.create_version(
            dataset_id=dataset_id,
            file_path=out_path,
            operations_json=ops_json,
            base_version_id=resolved_base_version_id,
            row_count=int(df2.shape[0]),
            col_count=int(df2.shape[1]),
            created_by=created_by,
            note=note,
        )
        return PreprocessApplyResponse(
            dataset_id=dataset_id,
            base_version_id=resolved_base_version_id,
            new_version_id=v.id,
            version_no=v.version_no,
            row_count=int(df2.shape[0]),
            col_count=int(df2.shape[1]),
        )

    # --- internal: resolve/read/write ---
    def _resolve_dataset_file(self, dataset_id: int, version_id: Optional[int]) -> Tuple[Dataset, str, Optional[int]]:
        """
        dataset_id, version_id를 기반으로 실제 로드할 파일 경로 결정
        """
        ds = self.versions.get_dataset(dataset_id)

        # 1. version_id가 주어진 경우 우선 처리
        if version_id is not None:
            v = self.versions.get_version(version_id)
            if v.dataset_id != dataset_id:
                raise ValueError("version_id does not belong to dataset_id")
            if not os.path.exists(v.file_path):
                raise FileNotFoundError(f"Version file missing: {v.file_path}")
            return ds, v.file_path, v.id

        # 2. 최신 버전 사용
        versions = self.versions.list_versions(dataset_id)
        if versions:
            v = versions[-1]
            if os.path.exists(v.file_path):
                return ds, v.file_path, v.id

        # 3. 원본 파일 경로 사용
        file_path = getattr(ds, "storage_path", None) or getattr(ds, "file_path", None) or getattr(ds, "path", None)
        if not file_path:
            raise FileNotFoundError("Dataset file path not found on dataset model")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset file missing: {file_path}")
        return ds, file_path, None

    def _read_dataframe(self, file_path: str) -> pd.DataFrame:
        """
        확장자에 따라 적절한 pandas 함수로 파일 읽기
        """
        ext = os.path.splitext(file_path.lower())[1]
        if ext in [".csv", ".txt"]:
            return pd.read_csv(file_path)
        if ext in [".xlsx", ".xls"]:
            return pd.read_excel(file_path)
        if ext in [".parquet"]:
            return pd.read_parquet(file_path)
        raise ValueError(f"Unsupported file type: {ext}")

    def _write_dataframe(self, df: pd.DataFrame, out_path: str) -> None:
        """
        dataframe을 지정된 경로에 저장
        """
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        ext = os.path.splitext(out_path.lower())[1]
        if ext == ".csv":
            df.to_csv(out_path, index=False)
            return
        if ext in [".parquet"]:
            df.to_parquet(out_path, index=False)
            return
        df.to_csv(out_path, index=False)

    def _make_versioned_path(self, ds: Dataset, version_no: int) -> str:
        """
        새 버전 파일이 저장될 경로 생성
        """
        base_path = getattr(ds, "storage_path", None) or getattr(ds, "file_path", None) or getattr(ds, "path", None)
        if not base_path:
            raise FileNotFoundError("Dataset file path not found on dataset model")

        base_dir = os.path.dirname(base_path)
        dataset_dir = os.path.join(base_dir, f"dataset_{ds.id}", "versions")
        return os.path.join(dataset_dir, f"v{version_no}.csv")

    # --- internal: operations ---
    def _apply_operations(self, df: pd.DataFrame, operations: List[PreprocessOperation]) -> pd.DataFrame:
        out = df.copy()

        for op in operations:
            name = op.op
            p = op.params or {}

            # 결측치 행 제거
            if name == "drop_missing":
                cols = p.get("columns") or []
                how = p.get("how", "any")
                if cols:
                    out = out.dropna(subset=cols, how=how)
                else:
                    out = out.dropna(how=how)

            #결측치 채우기 (평균, 중앙값, 최빈값, 특정값)
            elif name == "impute":
                method = p.get("method")  # "mean" | "median" | "mode" | "value"
                cols = p.get("columns") or []
                value = p.get("value", None)

                if not cols:
                    raise ValueError("impute requires 'columns'")

                for c in cols:
                    if c not in out.columns:
                        raise ValueError(f"Column not found: {c}")

                    if method == "mean":
                        out[c] = out[c].fillna(out[c].mean(numeric_only=True))
                    elif method == "median":
                        out[c] = out[c].fillna(out[c].median(numeric_only=True))
                    elif method == "mode":
                        m = out[c].mode(dropna=True)
                        fill = m.iloc[0] if len(m) else value
                        out[c] = out[c].fillna(fill)
                    elif method == "value":
                        out[c] = out[c].fillna(value)
                    else:
                        raise ValueError("impute.method must be one of: mean, median, mode, value")

            # 컬럼 삭제
            elif name == "drop_columns":
                cols = p.get("columns") or []
                out = out.drop(columns=cols, errors="ignore")

            # 컬럼 이름 변경
            elif name == "rename_columns":
                mapping = p.get("mapping") or {}
                if not isinstance(mapping, dict):
                    raise ValueError("rename_columns.mapping must be a dict")
                out = out.rename(columns=mapping)

            # 데이터 스케일링 (정규화, 표준화)
            elif name == "scale":
                method = p.get("method")  # "standardize" | "normalize"
                cols = p.get("columns") or []
                if not cols:
                    raise ValueError("scale requires 'columns'")

                for c in cols:
                    if c not in out.columns:
                        raise ValueError(f"Column not found: {c}")
                    s = pd.to_numeric(out[c], errors="coerce")

                    if method == "standardize":
                        mu = s.mean()
                        sd = s.std(ddof=0)
                        if sd == 0 or pd.isna(sd):
                            out[c] = s
                        else:
                            out[c] = (s - mu) / sd
                    elif method == "normalize":
                        mn = s.min()
                        mx = s.max()
                        denom = (mx - mn)
                        if denom == 0 or pd.isna(denom):
                            out[c] = s
                        else:
                            out[c] = (s - mn) / denom
                    else:
                        raise ValueError("scale.method must be one of: standardize, normalize")

            # 파생 변수 생성
            elif name == "derived_column":
                new_col = p.get("name")
                expr = p.get("expression")
                if not new_col or not expr:
                    raise ValueError("derived_column requires 'name' and 'expression'")

                # 보안 - 지원하지 않는 문자 포함 여부 검사
                if not _SAFE_EXPR_RE.match(expr):
                    # 문장 분리/다중문장 방지
                    if ";" in expr:
                        raise ValueError("derived_column.expression contains unsupported characters")

                    # 던더(특수 속성) 접근 차단
                    if "__" in expr:
                        raise ValueError("derived_column.expression contains unsupported pattern")

                    # 인덱싱/리터럴 확장 방지 (보안 레벨 유지)
                    if any(ch in expr for ch in ["[", "]", "{", "}"]):
                        raise ValueError("derived_column.expression contains unsupported characters")

                    # 단독 '='(할당처럼 보이는 케이스) 차단
                    # 허용: ==, >=, <=, !=  /  차단: a=b, x = y
                    if re.search(r"(?<![<>=!])=(?![=])", expr):
                        raise ValueError("derived_column.expression contains unsupported operator '='")

                    raise ValueError("derived_column.expression contains unsupported characters")

                # 참조된 컬럼이 실제로 존재하는지 확인
                tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr))
                unknown = [t for t in tokens if t not in out.columns and t not in {"and", "or"}]
                
                if unknown:
                    raise ValueError(f"derived_column.expression references unknown columns: {unknown}")

                out[new_col] = out.eval(expr, engine="python")

            else:
                raise ValueError(f"Unknown operation: {name}")

        return out
