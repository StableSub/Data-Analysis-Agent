# RAG 컴포넌트

## 책임

rag 컴포넌트는 retrieval QA 경로에서 dataset 인덱스를 준비하고, 질문과 관련된 근거를 검색한 뒤, 후속 응답 단계가 사용할 `rag_result`와 `insight`를 만든다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]
- [[architecture/components/guideline|Guideline 컴포넌트]]
- [[architecture/components/report|Report 컴포넌트]]

## 메인 그래프에서의 위치

- planner가 `route="retrieval_qa"`를 반환하면 진입한다.
- 종료 후 메인 그래프는 handoff를 보고 `visualization_flow` 또는 `merge_context`로 이동한다.

## 관련 구현 위치

- `backend/app/orchestration/workflows/rag.py`

## 진입 조건

- `source_id`가 있는 dataset 기반 질문이어야 한다.
- planner가 analysis 대신 retrieval QA를 선택해야 한다.

## 읽는 input state

- `user_input`
- `source_id`
- `model_id`

## 쓰는 output state

- `rag_index_status`
- `rag_result`
- `rag_data_exists`
- `insight`

## 내부 노드 목록

- `ensure_rag_index`
- `retrieve_context`
- `insight_synthesis`

## 하네스 계약

- node contract
  - `ensure_rag_index`, `retrieve_context`, `insight_synthesis`
- branch/status contract
  - index status는 `rag_service.ensure_index_for_source(...)` 결과를 따른다.
  - 문서화된 대표 status: `existing`, `created`, `dataset_missing`, `unsupported_format`
  - 검색 진행 조건: `existing`, `created`
- payload contract
  - consume: `user_input`, `source_id`, `model_id`, `rag_index_status`
  - produce: `rag_index_status`, `rag_result`, `rag_data_exists`, `insight`
  - `rag_result` key: `query`, `source_id`, `retrieved_chunks`, `context`, `retrieved_count`, `evidence_summary`
- approval contract
  - rag 컴포넌트는 `pending_approval`을 만들지 않는다.

## 노드 상세

### `ensure_rag_index`

- 역할
  - 대상 dataset의 RAG 인덱스 존재 여부를 확인하고 필요 시 생성한다.
- 입력
  - `source_id`
- 출력
  - `rag_index_status`
- 주요 로직
  - `rag_service.ensure_index_for_source(...)` 호출
  - status는 `existing`, `created`, `dataset_missing`, `unsupported_format` 같은 값이 될 수 있다
- 다음 분기
  - `retrieve_context`

### `retrieve_context`

- 역할
  - 질문 기준으로 관련 chunk를 검색하고 context를 만든다.
- 입력
  - `user_input`
  - `source_id`
  - `rag_index_status`
- 출력
  - `rag_result`
  - `rag_data_exists`
- 주요 로직
  - 인덱스 상태가 `existing` 또는 `created`일 때만 검색을 수행한다
  - 검색 결과를 `retrieved_chunks`, `context`, `retrieved_count`, `has_evidence`로 정리한다
  - 지원하지 않는 파일 형식이면 `evidence_summary`에 사유를 남긴다
- 다음 분기
  - `insight_synthesis`

### `insight_synthesis`

- 역할
  - 검색 결과를 짧은 insight 요약으로 정리한다.
- 입력
  - `rag_result`
  - `rag_data_exists`
  - `model_id`
- 출력
  - `insight`
  - 업데이트된 `rag_result`
- 주요 로직
  - 근거가 없으면 “직접 연결되는 근거를 찾지 못했다”는 요약만 남긴다
  - 근거가 있으면 `synthesize_insight(...)`를 호출해 `insight_summary`와 `evidence_summary`를 만든다
- 다음 분기
  - `END`

## merge_context와의 연결

- `rag_result`
  - retrieved chunks, evidence summary, has_evidence 정보를 유지한다
- `insight`
  - 메인 그래프가 `merge_context`에서 함께 합쳐 최종 응답용 context로 쓴다

## clarification / approval / fail 규칙

- clarification
  - rag 컴포넌트는 clarification을 직접 만들지 않는다.
- approval
  - approval 단계가 없다.
- fail
  - 근거가 없거나 인덱싱이 안 돼도 기본적으로 fail로 끝내지 않고 “근거 없음” 상태를 남긴다.
