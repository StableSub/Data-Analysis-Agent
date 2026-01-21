from sqlalchemy import Column, String, Integer, JSON, DateTime, LargeBinary, ForeignKey
from sqlalchemy.sql import func
from ...core.db import Base

class AnalysisResult(Base):
    """
    데이터 분석 결과(DataFrame 등)를 저장하는 테이블
    """
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, index=True)  
    
    # 필요 시 어떤 채팅/세션에서 나왔는지 연결 (선택 사항)
    # session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    
    # 데이터프레임을 JSON 형태로 저장 (DB에 따라 Text 타입 사용 고려)
    data_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChartResult(Base):
    """
    생성된 차트 이미지(PNG 등)를 저장하는 테이블
    """
    __tablename__ = "chart_results"

    id = Column(String(36), primary_key=True, index=True)  # chart_id
    
    # 이미지 바이너리 데이터 (BLOB)
    image_data = Column(LargeBinary, nullable=False)
    
    # 차트 생성에 사용된 설정(Spec)이나 메타데이터 저장 (선택 사항)
    #spec_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ViewSnapshot(Base):
    """
    사용자가 보고 있는 화면 상태(필터, 정렬 등이 적용된 데이터) 스냅샷
    """
    __tablename__ = "view_snapshots"

    # 스냅샷 토큰 (view_token)
    token = Column(String(64), primary_key=True, index=True)
    
    # 스냅샷 시점의 데이터 상태
    data_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())