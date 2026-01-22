"""
RAG 실제 PDF 테스트 시나리오:
1. 'tests/Deep Learning HW2.pdf' 파일을 읽어 텍스트로 추출
2. 추출된 텍스트를 임시 파일(txt)로 저장
3. DB에 Dataset 정보 등록
4. RagService를 통해 인덱싱 및 질의 테스트
5. 테스트 종료 후 임시 파일 및 데이터 정리

실행 방법:
    PYTHONPATH=. python backend/test_pdf_real.py
"""

import os
import pypdf  # PDF 파싱용 라이브러리
from pathlib import Path

from app.core.db import Base, engine, SessionLocal
from app.domain.data_source.models import Dataset
from app.rag import models as rag_models
from app.rag.core.embedding import E5Embedder
from app.rag.repository import RagRepository
from app.rag.service import RagService
from app.rag.types.errors import RagError, RagNotIndexedError
from app.ai.llm.client import LLMClient


def extract_text_from_pdf(pdf_path: Path) -> str:
    """PDF 파일에서 텍스트만 쏙 뽑아냅니다."""
    print(f"📖 [Parsing] PDF 읽는 중: {pdf_path}")
    text = ""
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        for page in reader.pages:
            text += page.extract_text() + "\n"
        print(f"   -> 총 {len(reader.pages)}페이지, {len(text)}글자 추출 완료.")
        return text
    except Exception as e:
        print(f"💥 PDF 읽기 실패: {e}")
        raise e


def run_pdf_demo() -> None:
    print("🚀 [Start] PDF RAG 통합 테스트 시작...")

    # 1. 파일 경로 설정
    # (이미지에 있던 그 파일 경로)
    target_pdf_path = Path("tests/Deep Learning HW2.pdf")

    # RAG가 읽을 수 있게 변환할 임시 텍스트 파일 경로
    temp_txt_path = Path("storage/temp_hw2_converted.txt")
    test_storage_dir = Path("storage/test_vector_store_pdf")

    # 파일 존재 확인
    if not target_pdf_path.exists():
        print(f"❌ 오류: 파일이 없습니다 -> {target_pdf_path}")
        return

    # 2. DB 초기화
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    dataset = None
    try:
        print("📦 [Setup] 서비스 초기화 중...")
        repo = RagRepository(db)
        embedder = E5Embedder()
        # ★ 중요: Gemini Flash 모델 사용 (API 키 확인 필수)
        llm_client = LLMClient(preset="gemini_flash")

        service = RagService(
            repository=repo,
            storage_dir=test_storage_dir,
            embedder=embedder,
        )

        # 3. PDF -> 텍스트 변환 및 임시 저장
        pdf_content = extract_text_from_pdf(target_pdf_path)

        # storage 폴더가 없으면 생성
        temp_txt_path.parent.mkdir(parents=True, exist_ok=True)
        temp_txt_path.write_text(pdf_content, encoding="utf-8")

        # 4. DB에 데이터셋 등록 (Real DB Model 사용)
        dataset = Dataset(
            filename="Deep Learning HW2.pdf",
            storage_path=str(temp_txt_path),  # 변환된 텍스트 파일을 가리킴
            encoding="utf-8",
            delimiter=None,
            filesize=len(pdf_content.encode("utf-8")),
            extra_metadata={"original_source": "pdf_test"},
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        # 5. 인덱싱 실행
        print(f"⚙️ [Indexing] 인덱싱 시작 (Source ID: {dataset.source_id})")
        # 혹시 모를 중복 방지
        service.delete_source(dataset.source_id)
        service.index_dataset(dataset)
        print("✅ 인덱싱 완료!")

        # 6. 질의응답 테스트
        query = "이 과제의 주제가 뭐야? 요약해줘."
        print(f"\n❓ [Question] {query}")

        try:
            retrieved = service.query(
                query=query,
                top_k=3,
                source_filter=[dataset.source_id],
            )
        except RagNotIndexedError:
            print("❌ 인덱스가 생성되지 않았습니다.")
            return

        if not retrieved:
            print("⚠️ 검색 결과가 없습니다.")
            return

        context = service.build_context(retrieved)
        answer = llm_client.ask(question=query, context=context)

        # 7. 결과 출력
        print("-" * 50)
        print(f"🤖 [Answer]\n{answer}\n")
        print("-" * 50)
        print("📚 [Evidence] 근거 청크:")
        for item in retrieved:
            # 줄바꿈 제거하고 100자만 미리보기
            snippet = item.content[:100].replace("\n", " ")
            print(f"- [Score: {item.score:.4f}] {snippet}...")

    except Exception as e:
        print(f"\n💥 에러 발생: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # 8. 뒷정리 (Cleanup)
        print("\n🧹 [Cleanup] 데이터 정리 중...")

        # DB 레코드 삭제
        if dataset and dataset.source_id:
            try:
                db.delete(dataset)
                db.commit()
            except:
                pass  # 이미 지워졌거나 에러 시 무시

        db.close()

        # 임시 텍스트 파일 삭제
        if temp_txt_path.exists():
            temp_txt_path.unlink()

        # 벡터 스토어 폴더 삭제 (재귀적 삭제)
        if test_storage_dir.exists():
            import shutil

            shutil.rmtree(test_storage_dir)

        print("✨ 테스트 종료")


if __name__ == "__main__":
    run_pdf_demo()
