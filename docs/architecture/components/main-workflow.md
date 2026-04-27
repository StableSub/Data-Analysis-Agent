# 메인 워크플로우 컴포넌트

## 책임

메인 워크플로우 컴포넌트는 사용자 질문을 intake 이후 적절한 하위 컴포넌트로 분기시키고, 각 단계의 결과를 조합해 최종 응답으로 연결하는 orchestration shell이다. 실제 런타임 조립의 system of record는 `backend/app/orchestration/builder.py`다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/preprocess|Preprocess 컴포넌트]]
- [[architecture/components/analysis|Analysis 컴포넌트]]
- [[architecture/components/rag|RAG 컴포넌트]]
- [[architecture/components/visualization|Visualization 컴포넌트]]
- [[architecture/components/report|Report 컴포넌트]]

## 메인 그래프에서의 위치

- 진입점
  - `START`
- 주요 연결
  - `intake_flow -> preprocess_flow -> analysis_flow 또는 rag_flow`
  - 이후 필요 시 `guideline_flow`, `visualization_flow`, `merge_context`, `report_flow`
  - terminal node: `general_question_terminal`, `clarification_terminal`, `data_qa_terminal`

## 진입 조건

- 모든 사용자 질문은 메인 그래프에서 시작한다.
- `source_id`가 비어 있으면 no-dataset handoff를 통해 일반 질문 또는 clarification 경로를 탄다.
- `source_id`가 있으면 dataset 기반 경로를 탄다.
- 별도 planner node는 없으며, planner 역할은 intake, handoff, 각 workflow 내부 계획 단계에 나뉘어 있다.

## 읽는 input state

- `user_input`
- `request_context`
- `source_id`
- `model_id`
- 이후 단계에서 누적되는 `handoff`, `preprocess_result`, `rag_result`, `guideline_result`, `analysis_result`, `visualization_result`, `merged_context`, `output`

## 쓰는 output state

- `handoff`
- `clarification_question`
- `merged_context`
- `output`

## 내부 노드 목록

- `intake_flow`
- `preprocess_flow`
- `analysis_flow`
- `rag_flow`
- `guideline_flow`
- `visualization_flow`
- `merge_context`
- `report_flow`
- `general_question_terminal`
- `clarification_terminal`
- `data_qa_terminal`

## 하네스 계약

- node contract
  - `intake_flow`, `general_question_terminal`, `clarification_terminal`, `preprocess_flow`, `analysis_flow`, `rag_flow`, `guideline_flow`, `visualization_flow`, `merge_context`, `data_qa_terminal`, `report_flow`
- branch/status contract
  - `handoff.next_step`: `general_question`, `data_pipeline`
  - preprocess 이후: `analysis`, `rag`, `cancelled`
  - analysis 이후: `guideline`, `visualization`, `merge_context`, `clarification`, `fail`
  - rag 이후: `guideline`, `visualization`, `merge_context`
  - guideline 이후: `visualization`, `merge_context`
  - visualization 이후: `merge_context`, `cancelled`
  - merge_context 이후: `report`, `data_qa`
- payload contract
  - consume: `user_input`, `request_context`, `handoff`, `preprocess_result`, `rag_result`, `guideline_index_status`, `guideline_result`, `insight`, `analysis_plan`, `analysis_result`, `visualization_result`, `clarification_question`, `model_id`
  - produce: `output`, `merged_context`
  - terminal `output.type`: `general_question`, `clarification`, `data_qa`, `report_answer`, `cancelled`
- merge_context applied-step contract
  - `preprocess_result.status == "applied"`
  - `rag_result.retrieved_count > 0`
  - `guideline_result.retrieved_count > 0`
  - `analysis_result.execution_status == "success"`
  - `visualization_result.status == "generated"`
- approval contract
  - 메인 builder는 approval을 직접 만들지 않는다.
  - `preprocess_flow`, `visualization_flow`, `report_flow`가 `pending_approval`과 resume 흐름을 소유한다.

## 노드 상세

### `intake_flow`

- 역할
  - dataset 유무만 먼저 판별해 초기 handoff를 만든다.
- 입력
  - `source_id`
- 출력
  - `handoff.next_step`
- 주요 로직
  - `source_id`가 비어 있으면 no-dataset intent로 `general_question` 또는 `clarification`을 결정한다
  - 값이 있으면 `analyze_intent(...)`를 통해 `handoff.next_step="data_pipeline"`과 각종 `ask_*` 플래그를 만든다
- 다음 분기
  - `general_question_terminal`
  - `clarification_terminal`
  - `preprocess_flow`

### `preprocess_flow`

- 역할
  - 전처리 판단, 계획, approval, 실제 실행을 담당하는 서브그래프를 수행한다.
- 입력
  - `handoff`
  - `dataset_profile`
  - `revision_request`
- 출력
  - `preprocess_decision`
  - `preprocess_plan`
  - `preprocess_result`
  - `pending_approval`
- 주요 로직
  - selected-dataset 요청은 모두 여기로 먼저 진입한다.
  - 서브그래프가 skip 또는 applied 결과를 만든 뒤 메인 그래프는 `handoff.ask_analysis`를 보고 `analysis_flow` 또는 `rag_flow`로 보낸다.
- 다음 분기
  - 성공 또는 skip면 `analysis_flow` 또는 `rag_flow`
  - 취소면 `END`

### `analysis_flow`

- 역할
  - analysis 서브그래프를 호출해 planning, execution, validation, persist를 수행한다.
- 입력
  - `handoff`
  - `user_input`
- 출력
  - `question_understanding`
  - `analysis_plan`
  - `analysis_result`
  - `analysis_error`
  - `final_status`
- 주요 로직
  - clarification이면 메인 그래프가 clarification terminal로 보낸다.
  - fail이면 메인 그래프가 종료한다.
  - success면 handoff를 보고 visualization 또는 merge_context로 보낸다.
  - 내부 execution 전략은 `analysis_plan.codegen_strategy`에 따라 SQL 또는 pandas sandbox 경로를 탄다.
- 다음 분기
  - `clarification_terminal`
  - `visualization_flow`
  - `merge_context`
  - fail이면 `END`

### `rag_flow`

- 역할
  - retrieval QA 서브그래프를 수행한다.
- 입력
  - `user_input`
  - `source_id`
- 출력
  - `rag_index_status`
  - `rag_result`
  - `insight`
- 주요 로직
  - 검색 evidence와 insight를 만든 뒤 `ask_guideline`, `ask_visualization` 플래그를 보고 다음 경로를 결정한다.
- 다음 분기
  - `guideline_flow`
  - `visualization_flow`
  - `merge_context`

### `guideline_flow`

- 역할
  - 활성 guideline이 있으면 관련 근거를 검색해 state에 적재한다.
- 입력
  - `user_input`
  - 활성 guideline 정보
- 출력
  - `guideline_index_status`
  - `guideline_result`
  - `guideline_context`(merged_context 내부 요약)
- 주요 로직
  - guideline 인덱스 확인/생성 후 검색과 요약 수행
- 다음 분기
  - `visualization_flow`
  - `merge_context`

### `visualization_flow`

- 역할
  - visualization 서브그래프를 수행한다.
- 입력
  - `analysis_result`
  - `analysis_plan`
  - `dataset_profile`
  - `revision_request`
- 출력
  - `visualization_plan`
  - `visualization_result`
  - `pending_approval`
- 주요 로직
  - 취소 시 메인 그래프가 종료하고, 그 외에는 `merge_context`로 이동한다.
  - 결과는 Vega-Lite spec 또는 legacy chart/image payload를 포함할 수 있다.
- 다음 분기
  - `merge_context`
  - 취소면 `END`

### `merge_context`

- 역할
  - 여러 단계의 산출물을 최종 응답용 context로 합친다.
- 입력
  - `request_context`
  - `handoff`
  - `preprocess_result`
  - `rag_result`
  - `guideline_result`
  - `guideline_context`
  - `insight`
  - `analysis_plan`
  - `analysis_result`
  - `visualization_result`
- 출력
  - `merged_context`
- 주요 로직
  - `builder.py` 내부 `merge_context_node(...)`가 state 필드들을 누적해 `merged_context`를 만든다.
- 다음 분기
  - `report_flow`
  - `data_qa_terminal`

### `report_flow`

- 역할
  - report 서브그래프를 수행한다.
- 입력
  - `analysis_result`
  - `visualization_result`
  - `guideline_result`
  - `merged_context`
- 출력
  - `report_draft`
  - `report_result`
  - `pending_approval`
  - `output`
- 주요 로직
  - report가 성공하면 `output.type="report_answer"`를 직접 만든다.
  - 취소/실패도 서브그래프 내부에서 정리한 뒤 종료한다.
- 다음 분기
  - 서브그래프 종료 후 메인 그래프도 `END`

### `general_question_terminal`

- 역할
  - dataset이 필요 없는 일반 질문에 즉시 답한다.
- 입력
  - `user_input`
  - `request_context`
  - `model_id`
- 출력
  - `output.type="general_question"`
  - `output.content`
- 주요 로직
  - `answer_general_question(...)` 호출

### `clarification_terminal`

- 역할
  - clarification 질문을 최종 응답으로 반환한다.
- 입력
  - `clarification_question`
- 출력
  - `output.type="clarification"`
  - `output.content`
- 주요 로직
  - state에 저장된 clarification 질문을 그대로 응답으로 사용

### `data_qa_terminal`

- 역할
  - merged context를 바탕으로 최종 데이터 응답을 만든다.
- 입력
  - `handoff`
  - `visualization_result`
  - `analysis_result`
  - `merged_context`
  - `user_input`
  - `model_id`
- 출력
  - `output.type="data_qa"`
  - `output.content`
- 주요 로직
  - `merged_context`를 그대로 `answer_data_question(...)`에 넘긴다.
  - 시각화 결과는 `merged_context`의 일부로 함께 전달된다.

## clarification / approval / fail 규칙

- clarification
  - intake 또는 analysis가 `clarification_question`을 만들면 메인 그래프는 `clarification_terminal`로 분기한다.
- approval
  - preprocess, visualization, report는 내부에서 `interrupt(...)`를 사용해 승인을 요구한다.
- fail
  - analysis/report 실패는 각 단계의 `output`과 `final_status`를 남긴 뒤 `END`로 종료한다
