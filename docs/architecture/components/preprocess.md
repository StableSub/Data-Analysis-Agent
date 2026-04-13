# Preprocess 컴포넌트

## 책임

preprocess 컴포넌트는 selected-dataset 요청이 들어왔을 때 dataset profile을 바탕으로 전처리가 필요한지 판단하고, 전처리 계획을 만든 뒤 approval 이후 실제 적용한다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]
- [[architecture/components/planner|Planner 컴포넌트]]
- [[architecture/components/analysis|Analysis 컴포넌트]]

## 메인 그래프에서의 위치

- 현재 브랜치에서는 selected-dataset 요청이 모두 먼저 `preprocess_flow`로 진입한다.
- 종료 후 메인 그래프는 `handoff.ask_analysis`를 보고 analysis 또는 rag로 이동한다.
- approval 취소 시 cancelled로 종료한다.

## 관련 구현 위치

- `backend/app/orchestration/workflows/preprocess.py`

## 진입 조건

- `source_id`가 존재해야 한다.
- dataset profile이 없으면 서브그래프 내부에서 먼저 생성한다.

## 읽는 input state

- `handoff`
- `user_input`
- `source_id`
- `dataset_profile`
- `revision_request`
- `model_id`

## 쓰는 output state

- `dataset_profile`
- `preprocess_decision`
- `preprocess_plan`
- `approved_plan`
- `pending_approval`
- `revision_request`
- `preprocess_result`
- 경우에 따라 `output`

## 내부 노드 목록

- `ingestion_and_profile`
- `preprocess_decision`
- `planner`
- `approval_gate`
- `executor`
- `skip`
- `cancel`

## 노드 상세

### `ingestion_and_profile`

- 역할
  - dataset profile이 아직 없으면 생성한다.
- 입력
  - `source_id`
  - 기존 `dataset_profile`
- 출력
  - `dataset_profile`
- 주요 로직
  - 이미 profile이 있으면 그대로 둔다.
  - 없으면 `preprocess_service.build_dataset_profile(...)` 호출
- 다음 분기
  - `preprocess_decision`

### `preprocess_decision`

- 역할
  - 현재 질문과 dataset profile을 바탕으로 전처리를 실행할지 생략할지 결정한다.
- 입력
  - `user_input`
  - `dataset_profile`
  - `handoff`
- 출력
  - `preprocess_decision`
- 주요 로직
  - `build_preprocess_decision(...)` 호출
  - 전처리 필요성이 없으면 `skip_preprocess`
- 다음 분기
  - `run_preprocess`면 `planner`
  - `skip_preprocess`면 `skip`

### `planner`

- 역할
  - 실제 전처리 계획을 만든다.
- 입력
  - `user_input`
  - `source_id`
  - `dataset_profile`
  - `revision_request`
  - `model_id`
- 출력
  - 보강된 `dataset_profile`
  - `preprocess_plan`
- 주요 로직
  - dataset profile에 recommendation이 없으면 EDA recommendation을 먼저 채운다.
  - 이후 `build_preprocess_plan(...)`으로 plan을 생성한다.
- 다음 분기
  - `approval_gate`

### `approval_gate`

- 역할
  - 전처리 계획을 사용자에게 검토받는다.
- 입력
  - `preprocess_plan`
  - `preprocess_decision`
  - `dataset_profile`
- 출력
  - `approved_plan`
  - `pending_approval`
  - `revision_request`
  - 취소 시 `preprocess_result`
  - 취소 시 `output.type="cancelled"`
- 주요 로직
  - `interrupt(payload)`로 승인/수정/취소 입력을 받는다.
  - approve면 승인된 plan을 저장한다.
  - revise면 같은 preprocess planner로 되돌릴 수정 요청을 남긴다.
  - cancel이면 즉시 cancelled 결과를 만든다.
- 다음 분기
  - approve면 `executor`
  - revise면 `planner`
  - cancel이면 `cancel`

### `executor`

- 역할
  - 승인된 전처리 계획을 실제로 적용한다.
- 입력
  - `source_id`
  - `preprocess_plan`
  - `approved_plan`
  - `dataset_profile`
- 출력
  - `preprocess_result`
- 주요 로직
  - `execute_preprocess_plan(...)` 호출
- 다음 분기
  - `END`

### `skip`

- 역할
  - 전처리 없이 다음 단계로 진행한다.
- 입력
  - 없음
- 출력
  - `preprocess_result.status="skipped"`
- 주요 로직
  - 전처리 생략 요약만 남기고 종료
- 다음 분기
  - `END`

### `cancel`

- 역할
  - 전처리 approval 취소 후 종료한다.
- 입력
  - 없음
- 출력
  - 별도 추가 출력 없음
- 주요 로직
  - approval gate에서 이미 취소 상태를 정리한 뒤 종료용 node만 수행
- 다음 분기
  - `END`

## approval / clarification / fail 규칙

- approval
  - preprocess는 항상 plan review approval을 사용한다.
  - approve / revise / cancel 3가지 분기만 가진다.
- clarification
  - preprocess 컴포넌트는 clarification을 직접 만들지 않는다.
- fail
  - 전처리 서브그래프 자체는 실패를 `preprocess_result.status="failed"`로 남길 수 있다.
  - 메인 그래프의 현재 분기 로직은 주로 cancelled 여부를 직접 보고, 그 외에는 다음 단계로 넘긴다.
  - cancel은 fail이 아니라 별도 cancelled 경로로 처리한다.
