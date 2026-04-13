# Guideline 컴포넌트

## 책임

guideline 컴포넌트는 활성 guideline이 있을 때 관련 근거를 검색하고 요약해, 최종 `merged_context`와 report가 참고할 guideline evidence를 만든다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/planner|Planner 컴포넌트]]
- [[architecture/components/rag|RAG 컴포넌트]]
- [[architecture/components/report|Report 컴포넌트]]

## 메인 그래프에서의 위치

- analysis 또는 rag 이후, `handoff.ask_guideline=true`일 때 실행될 수 있다.
- 이후에는 `visualization_flow` 또는 `merge_context`로 이어진다.

## 관련 구현 위치

- `backend/app/orchestration/workflows/guideline.py`

## 진입 조건

- analysis 또는 rag 이후 guideline 보조 근거가 필요하다고 판단된 경우 실행된다.
- 활성 guideline이 없더라도 서브그래프는 실행되며, 이 경우 “근거 없음” 상태를 명시적으로 남긴다.

## 읽는 input state

- `user_input`
- `model_id`
- 활성 guideline 정보

## 쓰는 output state

- `active_guideline_source_id`
- `guideline_index_status`
- `guideline_result`
- `guideline_data_exists`

## 내부 노드 목록

- `ensure_guideline_index`
- `retrieve_guideline_context`
- `summarize_guideline_evidence`

## 노드 상세

### `ensure_guideline_index`

- 역할
  - 활성 guideline이 있는지 확인하고 인덱스 상태를 준비한다.
- 입력
  - 활성 guideline 정보
- 출력
  - `active_guideline_source_id`
  - `guideline_index_status`
  - 경우에 따라 기본 `guideline_result`
- 주요 로직
  - 활성 guideline이 없으면 `status="no_active_guideline"`을 기록하고 서브그래프를 끝낸다.
  - 활성 guideline이 있으면 인덱스 존재 여부를 확인하고 필요한 경우 인덱싱한다.
- 다음 분기
  - `no_active_guideline`이면 `END`
  - 그 외에는 `retrieve_guideline_context`

### `retrieve_guideline_context`

- 역할
  - 질문 기준으로 guideline RAG 검색을 수행한다.
- 입력
  - `user_input`
  - `guideline_index_status`
  - `active_guideline_source_id`
- 출력
  - `guideline_result`
  - `guideline_data_exists`
- 주요 로직
  - 인덱스가 준비된 경우만 top-k 검색을 수행한다.
  - 검색 결과를 `retrieved_chunks`, `context`, `retrieved_count`, `has_evidence`로 정리한다.
- 다음 분기
  - `summarize_guideline_evidence`

### `summarize_guideline_evidence`

- 역할
  - 검색된 근거가 있으면 짧은 evidence summary를 생성한다.
- 입력
  - `guideline_result`
  - `guideline_data_exists`
  - `model_id`
- 출력
  - 업데이트된 `guideline_result`
- 주요 로직
  - 근거가 없으면 “활성 guideline 없음” 또는 “관련 근거 없음” 메시지를 유지한다.
  - 근거가 있으면 LLM을 호출해 `evidence_summary`를 만든다.
- 다음 분기
  - `END`

## merge_context / report와의 연결

- guideline 결과는 `builder.py`의 `merge_context_node(...)`에서 `guideline_context` 요약 형태로 합쳐진다.
- report와 final data answer는 이 merged guideline evidence를 간접적으로 사용한다.

## clarification / approval / fail 규칙

- clarification
  - guideline 컴포넌트는 clarification을 직접 만들지 않는다.
- approval
  - approval 단계가 없다.
- fail
  - 활성 guideline이 없거나 검색 결과가 없어도 fail로 처리하지 않고 상태를 명시적으로 남긴다.
