# Report 컴포넌트

## 책임

report 컴포넌트는 선택 데이터셋의 정량 지표와 분석/시각화/지침 결과를 바탕으로 리포트 초안을 만든 뒤 approval과 revision loop를 거쳐 최종 report 응답을 생성한다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]
- [[architecture/components/analysis|Analysis 컴포넌트]]
- [[architecture/components/visualization|Visualization 컴포넌트]]
- [[architecture/components/rag|RAG 컴포넌트]]
- [[architecture/components/guideline|Guideline 컴포넌트]]

## 메인 그래프에서의 위치

- `merge_context` 이후 `handoff.ask_report=true`일 때 진입한다.
- 성공하면 `output.type="report_answer"`를 만들고 메인 그래프는 바로 종료한다.

## 관련 구현 위치

- `backend/app/orchestration/workflows/report.py`

## 진입 조건

- `handoff.ask_report=true`
- report 생성에 사용할 `source_id`, `insight`, `visualization_result`, `merged_context` 중 일부가 준비돼 있어야 한다.

## 읽는 input state

- `user_input`
- `source_id`
- `analysis_result`
- `visualization_result`
- `guideline_result`
- `insight`
- `revision_request`
- `model_id`

## 쓰는 output state

- `report_draft`
- `report_result`
- `pending_approval`
- `revision_request`
- `output`

## 내부 노드 목록

- `report_draft`
- `approval_gate`
- `finalize`
- `cancel`

## 하네스 계약

- node contract
  - `report_draft`, `approval_gate`, `finalize`, `cancel`
- branch/status contract
  - approval decision: `approve`, `revise`, `cancel`
  - output type: `report_answer`, `cancelled`
  - revision gate: `revision_request.stage="report"`
- payload contract
  - consume: `user_input`, `source_id`, `analysis_result`, `visualization_result`, `guideline_result`, `insight`, `merged_context`, `revision_request`, `report_draft`, `model_id`
  - produce: `report_draft`, `report_result`, `pending_approval`, `revision_request`, `output`
  - final output: `output.type="report_answer"`, `output.content`
  - cancelled output: `output.type="cancelled"`
- approval contract
  - `pending_approval.stage="report"`
  - `pending_approval.kind="draft_review"`
  - `revision_request.stage="report"`
  - `approve`는 `finalize`, `revise`는 `report_draft`, `cancel`은 `cancel`로 이동한다.

## 노드 상세

### `report_draft`

- 역할
  - 리포트 초안을 생성한다.
- 입력
  - `user_input`
  - `source_id`
  - `insight`
  - `visualization_result`
  - `revision_request`
  - `model_id`
- 출력
  - `report_draft`
  - 비워진 `revision_request`
- 주요 로직
  - `resolve_target_source_id(...)`로 report 대상 source를 정한다.
  - insight summary와 visualization summary를 정리한다.
  - revision instruction이 있으면 revision count를 증가시킨다.
  - `report_service.build_report_draft(...)` 호출
- 다음 분기
  - `approval_gate`

### `approval_gate`

- 역할
  - 리포트 초안을 검토받고 approve/revise/cancel을 처리한다.
- 입력
  - `report_draft`
  - `source_id`
- 출력
  - `pending_approval`
  - `revision_request`
  - 취소 시 `output.type="cancelled"`
- 주요 로직
  - `interrupt(payload)`로 approve/revise/cancel 입력을 받는다
  - approve면 finalize로 진행한다
  - revise면 draft로 돌아갈 instruction을 저장한다
  - cancel이면 cancelled output을 만든다
- 다음 분기
  - approve면 `finalize`
  - revise면 `report_draft`
  - cancel이면 `cancel`

### `finalize`

- 역할
  - 승인된 리포트를 최종 응답으로 정리한다.
- 입력
  - `report_draft`
  - `session_id`
- 출력
  - `report_result`
  - 비워진 `pending_approval`
  - 비워진 `revision_request`
  - `output.type="report_answer"`
- 주요 로직
  - 초안 summary를 최종 `report_answer` output으로 옮긴다.
  - 현재 브랜치의 `finalize_node(...)`는 별도 persistence 호출 없이 응답 payload를 만든다.
- 다음 분기
  - `END`

### `cancel`

- 역할
  - approval 취소 후 종료한다.
- 입력
  - 없음
- 출력
  - 비워진 `pending_approval`
  - 비워진 `revision_request`
- 주요 로직
  - 취소 output은 approval gate가 이미 만들어 둔다
- 다음 분기
  - `END`

## revision loop와 최종 응답

- revision loop
  - `approval_gate`에서 `revise`가 선택되면 `report_draft`로 되돌아간다
  - revision instruction이 있으면 draft 생성 시 revision count가 증가한다
- 최종 응답
  - 성공 시 `output.type="report_answer"`를 report 컴포넌트가 직접 만든다
  - 메인 그래프는 별도 terminal node 없이 이 결과를 최종 output으로 사용한다

## approval / clarification / fail 규칙

- approval
  - report는 draft review approval을 사용한다
- clarification
  - report 컴포넌트는 clarification을 직접 만들지 않는다
- fail
  - 현재 report 서브그래프에는 별도 `fail` node가 없다.
  - cancel은 fail이 아니라 별도 cancelled output으로 처리한다.
