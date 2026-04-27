# Visualization 컴포넌트

## 책임

visualization 컴포넌트는 시각화 계획을 만들고, 필요하면 approval을 거쳐 실제 시각화 결과를 생성한다. analysis 결과로 바로 spec을 만들 수 있는 경우 fast path를 사용하고, 그렇지 않으면 planning path를 사용한다. 현재 생성 결과의 기본 형태는 Vega-Lite spec이며, legacy chart/image payload는 호환 용도로만 남아 있다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]
- [[architecture/components/analysis|Analysis 컴포넌트]]
- [[architecture/components/report|Report 컴포넌트]]

## 메인 그래프에서의 위치

- analysis 성공 후 `handoff.ask_visualization=true`일 때 진입한다.
- retrieval QA 이후에도 `ask_visualization=true`면 진입할 수 있다.
- 종료 후 메인 그래프는 `merge_context` 또는 `END(cancelled)`로 이동한다.

## 관련 구현 위치

- `backend/app/orchestration/workflows/visualization.py`

## 진입 조건

- `handoff.ask_visualization=true`
- 질문과 source_id가 있어야 한다.
- analysis 경로에서는 `analysis_result`와 `analysis_plan`이 있으면 fast path를 시도할 수 있다.

## 읽는 input state

- `user_input`
- `source_id`
- `analysis_result`
- `analysis_plan`
- `dataset_profile`
- `revision_request`
- `model_id`

## 쓰는 output state

- `visualization_plan`
- `visualization_result`
- `approved_plan`
- `pending_approval`
- `revision_request`
- 경우에 따라 `output`

## 내부 노드 목록

- `visualization_planner`
- `approval_gate`
- `visualization_executor`
- `cancel`

## 하네스 계약

- node contract
  - `visualization_planner`, `approval_gate`, `visualization_executor`, `cancel`
- branch/status contract
  - planner status: `analysis_generated`, `planned`
  - approval decision: `approve`, `revise`, `cancel`
  - result status: `generated`, `cancelled`
- payload contract
  - consume: `analysis_result`, `analysis_plan`, `source_id`, `dataset_profile`, `revision_request`, `model_id`, `user_input`
  - produce: `visualization_plan`, `visualization_result`, `approved_plan`, `pending_approval`, `revision_request`, `output`
  - `visualization_result` key: `status`, `source_id`, `summary`, `chart`, `artifact`, `renderer`, `vega_lite_spec`
  - cancelled output: `output.type="cancelled"`
- approval contract
  - `pending_approval.stage="visualization"`
  - `pending_approval.kind="plan_review"`
  - `revision_request.stage="visualization"`
  - `approve`는 `visualization_executor`, `revise`는 `visualization_planner`, `cancel`은 `cancel`로 이동한다.

## 노드 상세

### `visualization_planner`

- 역할
  - fast path 또는 planning path 중 하나를 선택해 시각화 준비를 한다.
- 입력
  - `analysis_result`
  - `analysis_plan`
  - `revision_request`
  - `source_id`
  - `user_input`
  - `dataset_profile`
  - `model_id`
- 출력
  - fast path면 `visualization_result`
  - 일반 path면 `visualization_plan`
- 주요 로직
  - `analysis_result`와 `analysis_plan`이 있고 수정 요청이 없으면 `build_from_analysis_result(...)`를 시도한다
  - 이 경우 `visualization_plan.status="analysis_generated"`와 함께 결과를 바로 만든다
  - fast path가 아니면 `build_visualization_plan(...)`으로 계획을 생성한다
  - fast path 결과는 `renderer="vega-lite"`, `vega_lite_spec`, summary를 포함할 수 있다
- 다음 분기
  - `status="analysis_generated"`면 `END`
  - `status="planned"`면 `approval_gate`
  - 그 외는 `visualization_executor`

### `approval_gate`

- 역할
  - 시각화 계획을 사용자에게 검토받는다.
- 입력
  - `visualization_plan`
  - `source_id`
- 출력
  - `approved_plan`
  - `pending_approval`
  - `revision_request`
  - 취소 시 `visualization_result`
  - 취소 시 `output.type="cancelled"`
- 주요 로직
  - preview row를 만든 뒤 `interrupt(payload)`로 approve/revise/cancel을 받는다
  - approve면 승인된 plan 저장
  - revise면 planner로 되돌릴 수정 요청 저장
  - cancel이면 cancelled 결과를 남긴다
- 다음 분기
  - approve면 `visualization_executor`
  - revise면 `visualization_planner`
  - cancel이면 `cancel`

### `visualization_executor`

- 역할
  - 승인된 시각화 계획을 실제 spec으로 finalize한다.
- 입력
  - `visualization_plan`
  - `approved_plan`
- 출력
  - `visualization_result`
  - 비워진 `revision_request`
  - 비워진 `approved_plan`
  - 비워진 `pending_approval`
- 주요 로직
  - `execute_visualization_plan(...)` 호출
  - 현재는 matplotlib PNG를 만들지 않고 Vega-Lite spec과 요약 정보를 만든다.
- 다음 분기
  - `END`

### `cancel`

- 역할
  - approval 취소 후 종료한다.
- 입력
  - 없음
- 출력
  - 별도 추가 출력 없음
- 주요 로직
  - approval gate가 이미 cancelled 상태를 남긴 뒤 종료용 node만 수행
- 다음 분기
  - `END`

## fast path와 planning path 차이

- fast path
  - analysis 결과와 plan이 이미 있고 수정 요청이 없을 때 사용
  - approval 없이 바로 결과를 생성할 수 있다
  - 기본 결과는 Vega-Lite spec + legacy chart_data 동시 제공일 수 있다
- planning path
  - 별도 시각화 계획을 만들고 approval을 거쳐 실행한다
  - preview row와 수정 루프를 지원한다
  - 실행 결과는 기본적으로 Vega-Lite spec을 반환한다

## approval / clarification / fail 규칙

- approval
  - 시각화 계획이 `planned` 상태일 때만 approval을 요구한다.
- clarification
  - visualization 컴포넌트는 clarification을 직접 만들지 않는다.
- fail
  - visualization 취소는 fail이 아니라 cancelled로 처리된다.
  - 메인 그래프는 cancelled만 별도 종료로 보고, 그 외 결과는 `merge_context`로 넘긴다.
