# 백엔드 역할 분리 / 아키텍처 설계서

## 1. 목적

- 이 문서는 현재 백엔드의 **최종 정리 기준 구조**를 정의한다.
- 기준은 `core + modules + orchestration`이다.
- 외부 계약은 유지한다.
  - FastAPI path
  - request/response shape
  - SSE 이벤트 이름
  - DB 스키마
  - 파일 저장 경로

## 2. 최종 판단

- 현재 백엔드는 단일 FastAPI 애플리케이션을 유지한다.
- 실구현 소유자는 `backend/app/core`, `backend/app/modules`, `backend/app/orchestration`만 가진다.
- 과거 top-level 기술 축이었던 `api`, `domain`, `rag`, `ai`, `data_eng`는 실구현에서 제거됐다.
- 따라서 현재 구조는 “헥사고날 전환”이 아니라, **모듈 책임 기준으로 재정렬된 단일 애플리케이션 구조**로 본다.

## 3. 현재 최종 구조

```text
backend/app/
  main.py
  dependencies.py

  core/
    db.py
    config.py

  modules/
    chat/
      router.py
      dependencies.py
      models.py
      repository.py
      schemas.py
      service.py
      session_service.py
      run_service.py

    datasets/
      router.py
      dependencies.py
      models.py
      repository.py
      schemas.py
      service.py
      storage.py
      reader.py
      encoding.py
      errors.py

    preprocess/
      router.py
      dependencies.py
      schemas.py
      service.py
      processor.py

    visualization/
      router.py
      dependencies.py
      schemas.py
      service.py

    rag/
      router.py
      dependencies.py
      models.py
      repository.py
      schemas.py
      service.py
      errors.py
      infra/
        embedding.py
        vector_store.py

    reports/
      router.py
      dependencies.py
      models.py
      repository.py
      schemas.py
      service.py
      metrics.py

    export/
      router.py
      dependencies.py
      schemas.py
      service.py

    results/
      models.py
      repository.py

  orchestration/
    client.py
    dependencies.py
    builder.py
    intake_router.py
    state.py
    utils.py
    workflows/
      preprocess.py
      rag.py
      visualization.py
      report.py
    tools/
```

## 4. 핵심 설계 원칙

### 4.1 router

- HTTP request 파싱
- HTTP status code 매핑
- response serialization
- SSE event framing

router는 service를 호출하는 얇은 진입점이어야 하며, repository나 workflow helper를 직접 조립하지 않는다.

### 4.2 service

- 기능 흐름 조합
- 모듈 내부 규칙 적용
- 모듈 내부 보조 객체 호출

service는 기능을 완성하는 계층이다.  
DB query, 파일 저장, CSV 읽기, metrics 계산, 벡터 인덱싱, 리포트 저장, 시각화 실행 같은 세부 구현은 필요 시 service 옆 보조 파일로 분리한다.

### 4.3 repository

- DB 접근만 담당한다.
- SQLAlchemy 세션을 받아 CRUD/조회만 수행한다.

### 4.4 orchestration

- 여러 module을 가로지르는 agent 실행 흐름만 담당한다.
- run/session/checkpointer/approval state를 유지한다.
- workflow planner, approval gate, main graph 조합을 담당한다.

orchestration은 repository를 직접 new 하지 않는다.  
필요한 기능은 `modules/*` service를 주입받아 사용한다.

### 4.5 core

- 앱 전체 공통 기반만 둔다.
- 현재 기준으로는 DB 연결과 최소 설정만 포함한다.

## 5. 책임 경계

### 5.1 datasets

- 데이터셋 업로드/목록/상세/샘플/삭제를 담당한다.
- 업로드/삭제 시 RAG lifecycle을 내부적으로 동반하지만, 이 결합은 datasets service 내부에 숨긴다.
- router는 RAG 예외 타입을 직접 알지 않는다.

### 5.2 chat

- 세션/메시지 persistence와 run 흐름을 분리한다.
- `session_service.py`는 durable session/message를 담당한다.
- `run_service.py`는 `run_id`, SSE relay, pending approval 조회, resume payload 조합을 담당한다.

### 5.3 preprocess

- direct preprocess API의 실행 엔진을 담당한다.
- dataset profile 계산과 operation 적용은 preprocess service/processor가 소유한다.
- plan 생성, approval, revision은 orchestration workflow가 담당한다.

### 5.4 visualization

- direct manual visualization API를 소유한다.
- 데이터 추출, preview 구성, 실행 코드 생성, 차트 렌더링 실행은 visualization service가 소유한다.
- chart 선택, approval, workflow state 갱신은 orchestration workflow가 담당한다.

### 5.5 rag

- 인덱싱, 검색, context 생성, source 삭제를 소유한다.
- direct `/rag/query`도 rag service를 통해 answer 조합까지 처리한다.
- vector store와 embedder의 실제 구현은 `modules/rag/infra/*`가 소유한다.

### 5.6 reports

- direct `/report` 생성과 persistence를 reports service가 소유한다.
- source 기준 metrics 계산은 `metrics.py`가 담당한다.
- chat workflow의 draft 생성/approval은 orchestration workflow가 담당한다.

### 5.7 export

- `analysis_results`를 읽어 CSV로 직렬화하는 흐름을 담당한다.
- `StreamingResponse`는 router에서 만든다.

### 5.8 results

- export 전제인 결과 저장 모델/조회만 담당한다.

## 6. main/dependencies 역할

- [main.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/main.py)
  - `modules/*` router만 등록한다.
  - `Base.metadata.create_all`과 CORS 설정만 가진다.
- [dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/dependencies.py)
  - 전역 shim 역할만 한다.
  - 실질 조립은 각 module의 `dependencies.py`와 [orchestration/dependencies.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/dependencies.py)가 맡는다.

## 7. 의도적으로 유지한 현행 제약

- direct `/report`, `/rag/query`에서 넘긴 `context`는 현재 의미 있게 반영되지 않는다.
- `SessionSource.session_id` 타입 불일치는 이번 구조 정리 범위 밖이다.
- run/approval state는 `InMemorySaver` 기반 비영속 상태다.

이 세 가지는 현재 구조 위반이 아니라, 별도 behavior/schema 개선 과제로 본다.

## 8. 완료 기준

현재 구조가 올바르게 유지되었다고 판단하는 기준은 아래와 같다.

- 실구현 소유자는 `core/modules/orchestration`만 가진다.
- router는 HTTP만 담당한다.
- service는 기능 흐름만 담당한다.
- repository는 DB만 담당한다.
- orchestration은 cross-module 조합만 담당한다.
- public API, SSE, DB, 파일 저장 경로는 기존 계약을 유지한다.
