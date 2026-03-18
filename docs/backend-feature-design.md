# 백엔드 기능별 상세 설계서

## 1. 목적

- 이 문서는 현재 백엔드의 기능 모듈을 **실제 구현 기준**으로 설명한다.
- 기준 구조는 [backend-architecture-guidelines.md](/Users/anjeongseob/Desktop/Project/capstone-project/docs/backend-architecture-guidelines.md)다.
- 목적은 각 모듈의 책임과 비책임을 분명히 해서, 수정 범위를 빠르게 결정할 수 있게 하는 것이다.

## 2. 공통 원칙

- `router.py`: HTTP 처리만 담당
- `service.py`: 기능 흐름만 담당
- `repository.py`: DB 접근만 담당
- 보조 파일: 파일 저장, CSV 읽기, metrics, processor, infra 구현 담당
- `orchestration/`: 여러 module을 가로지르는 run/workflow/approval만 담당

## 3. datasets

구현 위치

- [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/router.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/dependencies.py)
- [models.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/models.py)
- [repository.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/repository.py)
- [schemas.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/schemas.py)
- [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/service.py)
- [storage.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/storage.py)
- [reader.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/reader.py)
- [encoding.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/encoding.py)
- [errors.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/datasets/errors.py)

현재 책임

- 업로드
- 목록/상세/샘플 조회
- 삭제
- 업로드 시 RAG 인덱싱
- 삭제 시 best-effort RAG cleanup

비책임

- 수동 시각화 데이터 추출
- 채팅 run orchestration
- preprocess plan 생성

## 4. chat

구현 위치

- [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/router.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/dependencies.py)
- [models.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/models.py)
- [repository.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/repository.py)
- [schemas.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/schemas.py)
- [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/service.py)
- [session_service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/session_service.py)
- [run_service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/run_service.py)

현재 책임

- `session_service.py`
  - 세션 생성/조회
  - 메시지 append
  - history 조회
  - delete
- `run_service.py`
  - `run_id` 생성
  - SSE event relay
  - pending approval 조회
  - resume payload 조합
- `service.py`
  - router가 쓰는 상위 흐름 조합

비책임

- workflow builder 내부 구현
- dataset 파일 I/O
- RAG 인덱스 조작

## 5. preprocess

구현 위치

- [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/router.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/dependencies.py)
- [schemas.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/schemas.py)
- [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/service.py)
- [processor.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/preprocess/processor.py)

현재 책임

- dataset profile 계산
- 전처리 operation 적용
- 새 dataset 생성

비책임

- LLM plan 생성
- approval / revision / cancel

그 흐름은 [orchestration/workflows/preprocess.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/preprocess.py)가 담당한다.

## 6. visualization

구현 위치

- [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/router.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/dependencies.py)
- [schemas.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/schemas.py)
- [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/visualization/service.py)

현재 책임

- direct manual visualization 데이터 추출
- workflow용 sample frame 로드
- preview row 생성
- 실행 코드 생성
- 렌더링 실행

비책임

- 차트 타입 선택
- approval / revision / cancel

그 흐름은 [orchestration/workflows/visualization.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/visualization.py)가 담당한다.

## 7. rag

구현 위치

- [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/router.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/dependencies.py)
- [models.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/models.py)
- [repository.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/repository.py)
- [schemas.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/schemas.py)
- [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/service.py)
- [errors.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/errors.py)
- [infra/embedding.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/infra/embedding.py)
- [infra/vector_store.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/rag/infra/vector_store.py)

현재 책임

- dataset 인덱싱
- source 삭제
- vector retrieval
- context 구성
- direct `/rag/query` answer 조합

비책임

- 채팅 run orchestration
- 보고서 draft 생성

## 8. reports

구현 위치

- [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/router.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/dependencies.py)
- [models.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/models.py)
- [repository.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/repository.py)
- [schemas.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/schemas.py)
- [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/service.py)
- [metrics.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/reports/metrics.py)

현재 책임

- direct `/report` summary 생성
- report persistence / list / get
- source 기준 metrics 계산

비책임

- chat workflow 안의 draft approval state 관리

그 흐름은 [orchestration/workflows/report.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/report.py)가 담당한다.

## 9. export

구현 위치

- [router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/export/router.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/export/dependencies.py)
- [schemas.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/export/schemas.py)
- [service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/export/service.py)

현재 책임

- `analysis_results` 조회
- CSV 직렬화
- 파일명 생성

비책임

- HTTP streaming response 생성

## 10. results

구현 위치

- [models.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/results/models.py)
- [repository.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/results/repository.py)

현재 책임

- export가 참조하는 결과 저장 모델/조회

## 11. orchestration

구현 위치

- [client.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py)
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/dependencies.py)
- [builder.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/builder.py)
- [intake_router.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/intake_router.py)
- [state.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/state.py)
- [utils.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/utils.py)
- [workflows/preprocess.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/preprocess.py)
- [workflows/rag.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/rag.py)
- [workflows/visualization.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/visualization.py)
- [workflows/report.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/report.py)

현재 책임

- main graph 조립
- intake routing
- run/session/thread_id 조합
- approval state 생성/재개
- preprocess/rag/visualization/report workflow 조합

비책임

- repository 생성
- CSV 파일 직접 읽기
- dataset 파일 저장
- vector store 구현
- direct report persistence

즉, orchestration은 **cross-module 흐름 조합 계층**이다.
