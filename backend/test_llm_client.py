"""
간단한 통합 시나리오:
- DB 테이블 생성
- ChatService로 질문을 던져 세션/메시지 저장
- 히스토리를 읽어 출력

실행 예시 (프로젝트 루트에서):
    PYTHONPATH=backend python backend/test_llm_client.py
"""
import os

from app.core.db import Base, engine, SessionLocal
from app.domain.chat.repository import ChatRepository
from app.ai.orchestrator.chat_flow import ChatFlowOrchestrator
from app.domain.chat.service import ChatService
from app.ai.llm.client import LLMClient


def run_demo() -> None:
    # 테이블이 없으면 생성
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        repository = ChatRepository(db)
        preset = os.getenv("LLM_PRESET", "gemini_flash")
        llm_client = LLMClient(preset=preset)
        orchestrator = ChatFlowOrchestrator(llm_client=llm_client)
        service = ChatService(repository=repository, orchestrator=orchestrator)

        # 1) 질문 요청
        response = service.ask(question="테스트 질문입니다.", context="추가 컨텍스트")
        print(f"[ask] session_id={response.session_id}, answer={response.answer}")

        # 2) 히스토리 조회
        history = service.get_history(response.session_id)
        if history:
            print("[history]")
            for msg in history.messages:
                print(f"- ({msg.role}) {msg.content}")
        else:
            print("히스토리를 불러오지 못했습니다.")
    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
