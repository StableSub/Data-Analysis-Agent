import pandas as pd
from pathlib import Path
from typing import IO, Optional, Tuple, List, Dict, Any
import uuid
import os

from .models import Dataset
from .repository import DataSourceRepository
from ...data_eng.encoding_detector import EncodingDetector
from .schemas import ManualVizRequest


class DataSourceService:
    def __init__(self, repository: DataSourceRepository, storage_dir: Path) -> None:
        self.repository = repository
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True) # 업로드 디렉토리가 없으면 생성

    def _persist_file(self, file_stream: IO[bytes], filename: str) -> Tuple[Path, int]:
        """
        업로드된 파일 스트림을 storage_dir 아래에 저장하고, 최종 파일 크기를 반환
        """
        # 스트림 위치를 항상 처음으로 돌려놓기
        if hasattr(file_stream, "seek"):
            file_stream.seek(0)

        # 파일 이름 중복 방지
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        target_path = self.storage_dir / unique_name
        
        size = 0
        with open(target_path, "wb") as target:
            while chunk := file_stream.read(8192):  # 8192 bytes씩 읽기
                size += len(chunk)
                target.write(chunk)
    
        return target_path, size

    def upload_dataset(
        self,
        *,
        file_stream: IO[bytes],
        original_filename: str,
        display_name: Optional[str] = None,
        encoding: Optional[str] = None,
        delimiter: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Dataset:
        """
        업로드된 파일을 저장하고, Dataset 객체를 생성하여 DB에 저장
        """
        # 파일 저장 + 파일 크기 계산
        storage_path, size = self._persist_file(file_stream, original_filename)

        # 인코딩/구분자 자동 탐지
        metadata = EncodingDetector.detect_file_metadata(storage_path)
    
        # 사용자가 명시적으로 지정한 값이 있으면 우선 사용
        final_encoding = encoding if encoding else metadata.get('encoding')
        final_delimiter = delimiter if delimiter else metadata.get('delimiter')

        # Dataset ORM 객체 생성
        dataset = Dataset(
            filename=display_name or original_filename,
            storage_path=str(storage_path),
            encoding=final_encoding,
            delimiter=final_delimiter,
            line_ending=metadata.get('line_ending'),
            quotechar=metadata.get('quotechar'),
            escapechar=metadata.get('escapechar'),
            has_header=metadata.get('has_header', True),
            parse_status=metadata.get('parse_status', 'success'),
            filesize=size,
            extra_metadata=None,
            workspace_id=workspace_id,
        )
        return self.repository.create(dataset)
    
    def list_datasets(
        self,
        workspace_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Dataset]:
        """
        워크스페이스 단위 데이터 소스 목록 조회
        - workspace_id 가 주어지면 해당 워크스페이스 기준으로 필터링
        - 없으면 전체 데이터셋 기준
        - skip / limit 로 간단한 페이지네이션 처리
        """
        if workspace_id:
            datasets = self.repository.list_by_workspace(workspace_id)
        else:
            datasets = self.repository.list_all()

        # 간단한 슬라이싱 기반 페이지네이션
        end = skip + limit if limit is not None else None
        return datasets[skip:end]
    

    def get_dataset_detail(self, dataset_id: int) -> Optional[dict]:
        """
        단일 데이터 소스 상세 정보 반환.
        """
        dataset = self.repository.get_by_id(dataset_id)
        if not dataset:
            return None

        return {
            "dataset": dataset,
        }
        
    def delete_dataset(self, source_id: str) -> Dict[str, any]:
        """
        데이터 소스 삭제 (안전 삭제 처리 포함)
        - source_id로 데이터셋을 조회
        - 세션에서 사용 중인지 확인
        - 사용 중이 아닐 때만 실제 저장된 파일과 메타데이터(DB)를 함께 제거
        
        Returns:
            dict: 삭제 결과 정보
                - success: 삭제 성공 여부
                - in_use: 사용 중 여부
                - deleted_file: 삭제된 파일 정보 (source_id, filename, storage_path)
                - message: 결과 메시지
        """
        # 1. DB에서 데이터셋 조회
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return {
                "success": False,
                "in_use": False,
                "deleted_file": None,
                "message": "데이터셋을 찾을 수 없습니다.",
            }
        
        # 2. 세션에서 사용 중인지 확인 (안전 삭제 처리)
        if self.repository.is_dataset_in_use(source_id):
            return {
                "success": False,
                "in_use": True,
                "deleted_file": None,
                "message": "해당 데이터셋은 현재 세션에서 사용 중입니다.",
            }
        
        # 3. 삭제 전 파일 정보 백업 (응답용)
        deleted_info = {
            "source_id": dataset.source_id,
            "filename": dataset.filename,
            "storage_path": dataset.storage_path,
        }
        
        # 4. 실제 스토리지 파일 삭제
        storage_path = (Path(__file__).resolve().parent.parent.parent / "storage" / "datasets")
        if storage_path.exists():
            try:
                os.remove(storage_path)
            except Exception as e:
                # 파일 삭제 실패 시에도 DB는 삭제하도록 처리
                # (로깅 등 추가 가능)
                pass
        
        # 5. DB에서 메타데이터 삭제
        self.repository.delete(dataset)
        
        return {
            "success": True,
            "in_use": False,
            "deleted_file": deleted_info,
            "message": "데이터셋이 성공적으로 삭제되었습니다.",
        }
    
    def get_dataset_metadata(self, source_id: str) -> Optional[Dict]:
        """
        데이터 소스의 메타데이터 조회
        """
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset:
            return None
        
        return {
            'source_id': dataset.source_id,
            'encoding': dataset.encoding,
            'delimiter': dataset.delimiter,
            'line_ending': dataset.line_ending,
            'quotechar': dataset.quotechar,
            'escapechar': dataset.escapechar,
            'has_header': dataset.has_header,
            'parse_status': dataset.parse_status,
        }


    def update_dataset_metadata(
        self,
        source_id: str,
        encoding: Optional[str] = None,
        delimiter: Optional[str] = None,
        has_header: Optional[bool] = None
    ) -> Optional[Dict]:
        """
        데이터 소스의 메타데이터 수정
        
        필요 시 수동 보정 가능
        """
        updated_dataset = self.repository.update_metadata(
            source_id=source_id,
            encoding=encoding,
            delimiter=delimiter,
            has_header=has_header
        )
        
        if not updated_dataset:
            return None
        
        return {
            'source_id': updated_dataset.source_id,
            'encoding': updated_dataset.encoding,
            'delimiter': updated_dataset.delimiter,
            'has_header': updated_dataset.has_header,
            'updated': True
        }
        
    def get_dataset_sample(self, source_id: str, n_rows: int = 5) -> Optional[Dict]:
        """
        데이터셋 파일에서 상위 n개의 행을 읽어 샘플 데이터 반환
        """
        # 1. DB에서 데이터셋 정보 조회
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset or not dataset.storage_path:
            return None

        file_path = Path(dataset.storage_path)
        if not file_path.exists():
            return None

        try:
            # 2. 저장된 인코딩 및 구분자 정보를 사용하여 파일 읽기
            # csv 외의 형식 확장을 고려한다면 파일 확장자에 따른 분기 처리가 필요
            df = pd.read_csv(
                file_path,
                encoding=dataset.encoding or 'utf-8',
                sep=dataset.delimiter or ',',
                nrows=n_rows
            )

            return {
                "source_id": source_id,
                "columns": df.columns.tolist(),
                "rows": df.to_dict(orient='records')
            }
        except Exception as e:
            print(f"Error reading sample data: {e}")
            return None
    
    
    
    def get_manual_viz_data(self, request: "ManualVizRequest") -> Dict[str, Any]:
        """
        수동 시각화를 위한 샘플링 데이터 조회 및 컬럼 검증
        """
        # 1. 데이터셋 정보 조회
        dataset = self.repository.get_by_source_id(request.source_id)
        if not dataset:
            return {"error": "NOT_FOUND", "message": "데이터셋을 찾을 수 없습니다."}

        file_path = Path(dataset.storage_path)
        if not file_path.exists():
            return {"error": "FILE_NOT_FOUND", "message": "파일이 존재하지 않습니다."}

        try:
            # 2. 필요한 컬럼 리스트 추출
            requested_cols = [request.columns.x, request.columns.y]
            if request.columns.color:
                requested_cols.append(request.columns.color)
            if request.columns.group:
                requested_cols.append(request.columns.group)

            # 중복 제거
            requested_cols = list(set(requested_cols))

            # 3. 파일 읽기 (지정된 컬럼만, limit 적용)
            df = pd.read_csv(
                file_path,
                encoding=dataset.encoding or 'utf-8',
                sep=dataset.delimiter or ',',
                usecols=requested_cols,
                nrows=request.limit
            )

            if df.empty:
                return {"error": "NO_DATA", "message": "조회된 데이터가 없습니다."}

            # 4. 결과 반환
            return {
                "chart_type": request.chart_type,
                "data": df.to_dict(orient='records'),
                "summary": {
                    "row_count": len(df),
                    "source_id": request.source_id
                }
            }

        except ValueError as e:
            # usecols에 존재하지 않는 컬럼이 포함된 경우 발생
            return {"error": "INVALID_COLUMN", "message": str(e)}
        except Exception as e:
            return {"error": "INTERNAL_ERROR", "message": f"데이터 처리 중 오류: {str(e)}"}