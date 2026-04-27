# Analysis 컴포넌트

## 책임

analysis 컴포넌트는 질문 해석 이후의 planning, 실행 전략 선택, 결과 검증, 결과 저장을 담당한다. 현재 브랜치에서는 planner가 별도 node로 존재하지 않으므로, 실제 실행 가능한 `AnalysisPlan`을 확정하고 SQL 또는 pandas sandbox 실행 결과를 success/fail/clarification으로 정리하는 책임이 analysis 안에 더 많이 모여 있다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]
- [[architecture/components/preprocess|Preprocess 컴포넌트]]
- [[architecture/components/visualization|Visualization 컴포넌트]]
- [[architecture/components/report|Report 컴포넌트]]

## 메인 그래프에서의 위치

- preprocess 이후 `handoff.ask_analysis=true`일 때 진입한다.
- 종료 후 메인 그래프는 `clarification`, `fail`, `guideline`, `visualization`, `merge_context` 중 하나로 분기한다.

## 관련 구현 위치

- `backend/app/orchestration/workflows/analysis.py`
- `backend/app/modules/analysis/service.py`

## 진입 조건

- `user_input`이 비어 있지 않아야 한다.
- 유효한 `source_id`가 있어야 한다.

## 읽는 input state

- `user_input`
- `source_id`
- `model_id`
- 일부 경우 `analysis_plan`

## 쓰는 output state

- `dataset_meta`
- `question_understanding`
- `column_grounding`
- `analysis_plan_draft`
- `analysis_plan`
- `generated_code`
- `validated_code`
- `sandbox_result`
- `analysis_result`
- `analysis_error`
- `analysis_result_id`
- `retry_count`
- `clarification_question`
- `final_status`
- 경우에 따라 `output`

## 내부 노드 목록

- `analysis_planning`
- `analysis_clarification`
- `analysis_execution`
- `analysis_validation`
- `analysis_persist_result`

## 하네스 계약

- node contract
  - `analysis_planning`, `analysis_clarification`, `analysis_execution`, `analysis_validation`, `analysis_persist_result`
- branch/status contract
  - `final_status`: `planning`, `needs_clarification`, `executing`, `success`, `fail`
  - routing checks: `needs_clarification`, `fail`, `success`
  - `analysis_result.execution_status`: `success`
- payload contract
  - consume: `user_input`, `source_id`, `model_id`, `analysis_plan`, `session_id`
  - produce: `dataset_meta`, `question_understanding`, `column_grounding`, `analysis_plan_draft`, `analysis_plan`, `generated_code`, `validated_code`, `sandbox_result`, `analysis_result`, `analysis_error`, `retry_count`, `final_status`, `clarification_question`, `analysis_result_id`, `output`
  - failed output: `output.type="analysis_failed"`
- approval contract
  - analysis 컴포넌트는 `pending_approval`을 만들지 않는다.

## 노드 상세

### `analysis_planning`

- 역할
  - 질문 해석 이후 planning 전체를 수행하고, clarification이 필요한지 먼저 판별한다.
- 입력
  - `user_input`
  - `source_id`
  - `model_id`
- 출력
  - `dataset_meta`
  - `question_understanding`
  - `column_grounding`
  - `analysis_plan_draft`
  - `analysis_plan`
  - `clarification_question`
  - `analysis_error`
  - `analysis_result`
  - `final_status`
  - 경우에 따라 `output`
- 주요 로직
  - `user_input`이 비어 있으면 즉시 fail
  - `analysis_service.build_dataset_metadata(...)`로 metadata snapshot을 만든다
  - `build_question_understanding(...)`, `ground_columns(...)`, `build_analysis_plan_draft(...)`, `validate_and_finalize_plan(...)` 순서로 진행한다
  - 질문 해석이나 plan draft가 모호하면 `final_status="needs_clarification"`
  - 성공이면 `analysis_plan`과 planning 산출물을 모두 state에 적재
  - 예외가 나면 `plan_validation` 오류로 fail
- 다음 분기
  - `needs_clarification`면 `analysis_clarification`
  - `fail`이면 `END`
  - 그 외에는 `analysis_execution`

### `analysis_clarification`

- 역할
  - clarification 상태를 메인 그래프가 소비할 수 있게 정리한다.
- 입력
  - `clarification_question`
- 출력
  - `final_status="needs_clarification"`
  - `clarification_question`
  - `analysis_plan=None`
- 주요 로직
  - clarification 질문만 정리하고 종료
- 다음 분기
  - `END`

### `analysis_execution`

- 역할
  - 최종 `analysis_plan`을 기반으로 실행 경로를 선택하고, SQL 또는 pandas sandbox 실행을 수행한다.
- 입력
  - `user_input`
  - `source_id`
  - `analysis_plan`
  - `model_id`
- 출력
  - `generated_code`
  - `validated_code`
  - `sandbox_result`
  - `analysis_result`
  - `analysis_error`
  - `retry_count`
  - `final_status="executing"`
- 주요 로직
  - `resolve_target_source_id(...)`로 실제 target source를 다시 결정한다
  - dataset을 다시 읽는다
  - dataset이 없으면 `sandbox_execution` 오류로 fail 결과를 만든다
  - `analysis_plan.codegen_strategy="sql"`이면 DuckDB SQL 실행 경로를 탄다
  - 그 외에는 기존 `_run_code_generation_loop(...)`로 pandas 코드 생성/repair/sandbox 실행을 수행한다
  - 생성 코드 또는 SQL, 검증 코드, sandbox 결과, 실행 결과를 state에 적재
- 다음 분기
  - `analysis_validation`

### `analysis_validation`

- 역할
  - execution 결과를 해석해 최종 success/fail을 확정한다.
- 입력
  - `analysis_result`
  - `analysis_error`
- 출력
  - `final_status`
  - 실패 시 `analysis_error`
  - 실패 시 `output.type="analysis_failed"`
- 주요 로직
  - `analysis_result`가 없으면 즉시 fail
  - `execution_status=="success"`면 `final_status="success"`
  - 실패인데 `analysis_error`가 없으면 새 오류를 만들어 fail
  - 실패인데 기존 오류가 있으면 그 메시지로 fail
- 다음 분기
  - success면 `analysis_persist_result`
  - fail이면 `END`

### `analysis_persist_result`

- 역할
  - 성공한 분석 결과를 results 저장소에 기록한다.
- 입력
  - `user_input`
  - `source_id`
  - `session_id`
  - `analysis_plan`
  - `generated_code`
  - `analysis_result`
- 출력
  - `analysis_result_id`
  - 저장 실패 시 `analysis_error`
  - 저장 실패 시 `final_status="fail"`
  - 저장 실패 시 `output.type="analysis_failed"`
- 주요 로직
  - `_persist_result(...)` 호출
  - 저장 예외는 `persist_result` 오류로 fail 처리
- 다음 분기
  - `END`

## clarification / validation / persist 규칙

- clarification
  - intake 단계에서 바로 clarification이 나지 않았더라도, analysis planning 과정에서 모호성이 드러나면 clarification으로 회수될 수 있다.
- validation
  - execution이 성공해도 `analysis_validation`이 최종 success를 확정해야 다음 단계로 이동한다.
- persist
  - persist는 success 이후 마지막 단계다.
  - 저장 실패는 실행 성공과 별도로 `final_status="fail"`로 뒤집을 수 있다.

## 실행 전략

- `codegen_strategy="llm_codegen"`
  - 기존 pandas 코드 생성 + sandbox 실행 경로
- `codegen_strategy="sql"`
  - DuckDB를 사용해 CSV를 `dataset` 뷰로 등록한 뒤 SELECT 쿼리를 실행하는 경로
- SQLite는 analysis SQL 실행 엔진이 아니라 기존 app persistence/checkpoint 용도로 유지된다.
