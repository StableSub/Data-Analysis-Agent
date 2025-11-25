import chardet
import csv
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from io import StringIO


class EncodingDetector:
    """
    파일의 인코딩과 구분자를 자동으로 탐지하는 클래스
    """
    
    # 지원하는 인코딩 목록
    SUPPORTED_ENCODINGS = ['utf-8', 'cp949', 'euc-kr', 'iso-8859-1', 'utf-16le', 'utf-16be']
    
    # 지원하는 구분자 목록
    COMMON_DELIMITERS = [',', '\t', '|', ';']
    
    @staticmethod
    def detect_encoding(file_path: Path, sample_size: int = 65536) -> Dict[str, any]:
        """
        파일의 인코딩을 탐지
        
        Args:
            file_path: 분석할 파일 경로
            sample_size: 샘플링할 바이트 크기 (기본 64KB, 최대 100줄)
            
        Returns:
            dict: {
                'encoding': 탐지된 인코딩 (utf-8, cp949 등),
                'confidence': 신뢰도 (0.0 ~ 1.0),
                'bom_detected': BOM 검출 여부
            }
        """
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
        
        # BOM 체크
        bom_encoding = EncodingDetector._check_bom(raw_data)
        if bom_encoding:
            return {
                'encoding': bom_encoding,
                'confidence': 1.0,
                'bom_detected': True
            }
        
        # chardet으로 인코딩 탐지
        result = chardet.detect(raw_data)
        detected_encoding = result.get('encoding', 'unknown').lower()
        confidence = result.get('confidence', 0.0)
        
        # 인코딩 정규화 (euc-kr -> cp949)
        if detected_encoding in ['euc-kr', 'euc_kr']:
            detected_encoding = 'cp949'
        elif detected_encoding in ['iso-8859-1', 'iso_8859_1']:
            detected_encoding = 'iso-8859-1'
        
        # 지원하지 않는 인코딩이면 unknown
        if detected_encoding not in EncodingDetector.SUPPORTED_ENCODINGS:
            detected_encoding = 'unknown'
        
        return {
            'encoding': detected_encoding,
            'confidence': confidence,
            'bom_detected': False
        }
    
    @staticmethod
    def _check_bom(data: bytes) -> Optional[str]:
        """
        BOM(Byte Order Mark) 확인
        
        Returns:
            str: BOM이 감지되면 인코딩 반환, 없으면 None
        """
        if data.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        elif data.startswith(b'\xff\xfe'):
            return 'utf-16le'
        elif data.startswith(b'\xfe\xff'):
            return 'utf-16be'
        return None
    
    @staticmethod
    def detect_delimiter(
        file_path: Path,
        encoding: str,
        sample_lines: int = 100
    ) -> Dict[str, any]:
        """
        CSV 파일의 구분자를 탐지
        
        Args:
            file_path: 분석할 파일 경로
            encoding: 파일 인코딩
            sample_lines: 분석할 샘플 줄 수
            
        Returns:
            dict: {
                'delimiter': 탐지된 구분자 (,, \t, | 등),
                'quotechar': 따옴표 문자,
                'has_header': 헤더 존재 여부,
                'confidence': 신뢰도
            }
        """
        try:
            # 파일 읽기
            with open(file_path, 'r', encoding=encoding) as f:
                sample = ''.join([f.readline() for _ in range(sample_lines)])
            
            # csv.Sniffer로 구분자 추정
            sniffer = csv.Sniffer()
            
            # 구분자 탐지
            try:
                dialect = sniffer.sniff(sample, delimiters=''.join(EncodingDetector.COMMON_DELIMITERS))
                delimiter = dialect.delimiter
                quotechar = dialect.quotechar
            except csv.Error:
                # Sniffer 실패 시 빈도 기반 추정
                delimiter = EncodingDetector._estimate_delimiter_by_frequency(sample)
                quotechar = '"'
            
            # 헤더 존재 여부 확인
            has_header = False
            try:
                has_header = sniffer.has_header(sample)
            except csv.Error:
                # has_header 실패 시 False로 처리
                pass
            
            # 구분자 검증 (일관성 체크)
            confidence = EncodingDetector._validate_delimiter(sample, delimiter)
            
            # 신뢰도가 너무 낮으면 auto_failed
            if confidence < 0.5:
                delimiter = 'auto_failed'
            
            return {
                'delimiter': delimiter,
                'quotechar': quotechar,
                'has_header': has_header,
                'confidence': confidence
            }
            
        except Exception as e:
            return {
                'delimiter': 'auto_failed',
                'quotechar': '"',
                'has_header': False,
                'confidence': 0.0
            }
    
    @staticmethod
    def _estimate_delimiter_by_frequency(sample: str) -> str:
        """
        각 구분자의 빈도를 계산하여 가장 많이 등장하는 구분자 선택
        """
        delimiter_counts = {delim: sample.count(delim) for delim in EncodingDetector.COMMON_DELIMITERS}
        
        # 가장 빈도가 높은 구분자 선택
        if max(delimiter_counts.values()) > 0:
            return max(delimiter_counts, key=delimiter_counts.get)
        
        return ','  # 기본값
    
    @staticmethod
    def _validate_delimiter(sample: str, delimiter: str) -> float:
        """
        구분자의 일관성을 검증하여 신뢰도 반환
        각 줄마다 구분자 개수가 일관적인지 확인
        """
        lines = sample.strip().split('\n')
        if len(lines) < 2:
            return 0.0
        
        # 각 줄의 구분자 개수 계산
        counts = [line.count(delimiter) for line in lines if line.strip()]
        
        if not counts:
            return 0.0
        
        # 가장 빈번한 개수
        most_common_count = max(set(counts), key=counts.count)
        
        # 일관성 비율 계산
        consistency = sum(1 for c in counts if c == most_common_count) / len(counts)
        
        return consistency
    
    @staticmethod
    def detect_file_metadata(file_path: Path) -> Dict[str, any]:
        """
        파일의 인코딩과 구분자를 한 번에 탐지
        
        Returns:
            dict: {
                'encoding': 인코딩,
                'delimiter': 구분자,
                'quotechar': 따옴표,
                'line_ending': 줄바꿈 문자,
                'escapechar': 이스케이프 문자,
                'has_header': 헤더 존재 여부,
                'parse_status': 'success' | 'tentative' | 'failed'
            }
        """
        # 1. 인코딩 탐지
        encoding_result = EncodingDetector.detect_encoding(file_path)
        encoding = encoding_result['encoding']
        
        # 인코딩 실패
        if encoding == 'unknown':
            return {
                'encoding': 'unknown',
                'delimiter': 'auto_failed',
                'quotechar': '"',
                'line_ending': '\n',
                'escapechar': None,
                'has_header': False,
                'parse_status': 'failed'
            }
        
        # 2. 구분자 탐지
        delimiter_result = EncodingDetector.detect_delimiter(file_path, encoding)
        
        # 3. 줄바꿈 문자 탐지
        line_ending = EncodingDetector._detect_line_ending(file_path, encoding)
        
        # 4. 파싱 상태 결정
        parse_status = 'success'
        if delimiter_result['delimiter'] == 'auto_failed':
            parse_status = 'failed'
        elif delimiter_result['confidence'] < 0.8:
            parse_status = 'tentative'
        
        return {
            'encoding': encoding,
            'delimiter': delimiter_result['delimiter'],
            'quotechar': delimiter_result.get('quotechar', '"'),
            'line_ending': line_ending,
            'escapechar': None,  # 기본값
            'has_header': delimiter_result.get('has_header', False),
            'parse_status': parse_status
        }
    
    @staticmethod
    def _detect_line_ending(file_path: Path, encoding: str) -> str:
        """
        줄바꿈 문자 탐지 (\n, \r\n, \r)
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(1024)
            
            if '\r\n' in sample:
                return '\\r\\n'
            elif '\r' in sample:
                return '\\r'
            else:
                return '\\n'
        except:
            return '\\n'  # 기본값