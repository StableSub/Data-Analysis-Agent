# Orchestration workflow wrappers

`backend/app/orchestration/workflows/` 아래 파일들은 main graph에서 호출되는 subgraph wrapper다. 각 wrapper는 module service를 직접 실행하는 순서와 approval/clarification/cancel route를 정의한다. 실제 business rule은 `backend/app/modules/`가 소유한다.

## 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/orchestration/workflows/__init__.py` | workflows package marker다. |
| `backend/app/orchestration/workflows/analysis.py` | 질문 이해 → plan → code generation/execution → validation → persist 흐름을 조립한다. |
| `backend/app/orchestration/workflows/guideline.py` | active guideline index 확인, retrieval, evidence summary subgraph를 조립한다. |
| `backend/app/orchestration/workflows/preprocess.py` | ingestion/profile → preprocess decision → plan → approval → execute/skip/cancel 흐름을 조립한다. |
| `backend/app/orchestration/workflows/rag.py` | dataset RAG index 확인, retrieval, insight synthesis 흐름을 조립한다. |
| `backend/app/orchestration/workflows/report.py` | report draft → approval → finalize/revise/cancel 흐름을 조립한다. |
| `backend/app/orchestration/workflows/visualization.py` | visualization plan → approval → execute/revise/cancel 또는 analysis-generated direct result 흐름을 조립한다. |

## 하네스 계약

이 섹션은 workflow wrapper와 main graph가 공유하는 route/status/payload vocabulary를 한곳에 모은다. `backend/tests/test_architecture_docs.py`는 이 용어들이 문서에서 사라지면 architecture drift로 본다.

### Main workflow

- route/status: `general_question`, `data_pipeline`, `analysis`, `rag`, `guideline`, `visualization`, `merge_context`, `clarification`, `fail`, `cancelled`, `report`, `data_qa`, `report_answer`, `applied`, `generated`.
- payload contract: `user_input`, `request_context`, `handoff`, `preprocess_result`, `rag_result`, `guideline_index_status`, `guideline_result`, `insight`, `analysis_plan`, `analysis_result`, `visualization_result`, `clarification_question`, `model_id`, `output`, `merged_context`.

### Analysis workflow

- route/status: `planning`, `needs_clarification`, `executing`, `success`, `fail`, `analysis_failed`.
- payload contract: `user_input`, `source_id`, `model_id`, `analysis_plan`, `session_id`, `dataset_meta`, `question_understanding`, `column_grounding`, `analysis_plan_draft`, `generated_code`, `validated_code`, `sandbox_result`, `analysis_result`, `analysis_error`, `retry_count`, `final_status`, `clarification_question`, `analysis_result_id`, `output`.

### Guideline workflow

- route/status: `no_active_guideline`, `existing`, `created`, `missing`, `retrieved`, `no_evidence`.
- payload contract: `user_input`, `model_id`, `active_guideline_source_id`, `guideline_index_status`, `guideline_result`, `guideline_data_exists`, `retrieved_chunks`, `retrieved_count`, `evidence_summary`, `status`.

### Preprocess workflow

- route/status: `run_preprocess`, `skip_preprocess`, `approve`, `revise`, `cancel`, `skipped`, `applied`, `failed`, `cancelled`.
- payload contract: `source_id`, `dataset_profile`, `handoff`, `revision_request`, `user_input`, `model_id`, `preprocess_decision`, `preprocess_plan`, `approved_plan`, `pending_approval`, `preprocess_result`, `output`, `output_source_id`.
- approval contract: `pending_approval.stage="preprocess"`, `pending_approval.kind="plan_review"`, `revision_request.stage="preprocess"`.

### RAG workflow

- route/status: `existing`, `created`, `dataset_missing`, `unsupported_format`.
- payload contract: `user_input`, `source_id`, `model_id`, `rag_index_status`, `rag_result`, `rag_data_exists`, `insight`, `retrieved_chunks`, `retrieved_count`, `evidence_summary`.

### Visualization workflow

- route/status: `analysis_generated`, `planned`, `approve`, `revise`, `cancel`, `generated`, `cancelled`.
- payload contract: `analysis_result`, `analysis_plan`, `source_id`, `dataset_profile`, `revision_request`, `model_id`, `user_input`, `visualization_plan`, `visualization_result`, `approved_plan`, `pending_approval`, `output`, `renderer`, `vega_lite_spec`.
- approval contract: `pending_approval.stage="visualization"`, `pending_approval.kind="plan_review"`, `revision_request.stage="visualization"`.

### Report workflow

- route/status: `approve`, `revise`, `cancel`, `report_answer`, `cancelled`.
- payload contract: `user_input`, `source_id`, `analysis_result`, `visualization_result`, `guideline_result`, `insight`, `merged_context`, `revision_request`, `report_draft`, `model_id`, `report_result`, `pending_approval`, `output`.
- approval contract: `pending_approval.stage="report"`, `pending_approval.kind="draft_review"`, `revision_request.stage="report"`.

## Analysis workflow: `backend/app/orchestration/workflows/analysis.py`

### Node

- `analysis_planning`: user question/source id를 받아 dataset metadata, question understanding, column grounding, plan draft, final plan을 만든다.
- `analysis_clarification`: ambiguity가 남은 경우 `clarification_question`과 `final_status="needs_clarification"`를 유지한다.
- `analysis_execution`: plan 기반 generated code, validated code, sandbox result, execution result를 만든다.
- `analysis_validation`: execution result를 최종 검증하고 `final_status`를 성공/실패로 정리한다.
- `analysis_persist_result`: 성공 result를 저장하고 `analysis_result_id` state update를 반환한다.

### Route

- `START` → `analysis_planning`.
- planning 후 `needs_clarification` → `analysis_clarification`, `fail` → `END`, 그 외 → `analysis_execution`.
- execution → validation 후 success면 persist, 그 외는 `END`로 이어진다.

### 주의점

- `final_status="needs_clarification"`은 main graph의 `clarification_terminal`로 이어진다.
- `final_status="fail"`은 main graph에서 `END`로 종료된다.
- `analysis_result_id`는 `analysis_persist_result_node()`가 성공 시 반환하는 동적 state update이며, `state.py`의 `AnalysisGraphState` TypedDict에 정적으로 선언된 key는 아니다.

## Guideline workflow: `backend/app/orchestration/workflows/guideline.py`

### Node

- `ensure_guideline_index`: active guideline이 있는지 확인하고 index status를 만든다.
- `retrieve_guideline_context`: guideline query를 수행해 chunks/context를 만든다.
- `summarize_guideline_evidence`: retrieved evidence를 요약하거나 no-evidence 상태를 만든다.

### State/output

- `active_guideline_source_id`, `guideline_index_status`, `guideline_data_exists`, `guideline_result`가 주요 key다.
- `guideline_result.status`, `retrieved_count`, `evidence_summary`, `filename`, `guideline_id`가 downstream `merged_context.guideline_context`에 반영된다.

### 주의점

- active guideline이 없으면 `no_active_guideline` 성격의 status로 끝날 수 있다.
- guideline evidence가 없다는 것은 workflow 실패와 다르다.

## Preprocess workflow: `backend/app/orchestration/workflows/preprocess.py`

### Node

- `ingestion_and_profile`: target source id의 dataset profile을 만든다.
- `preprocess_decision`: 질문과 profile로 preprocess 필요 여부를 판단한다.
- `planner`: preprocess plan/review payload를 만든다.
- `approval_gate`: `interrupt(payload)`로 approve/revise/cancel 결정을 기다린다.
- `executor`: 승인된 plan을 적용하고 `preprocess_result`를 만든다.
- `skip`: preprocess가 필요 없을 때 `status="skipped"` 결과를 만든다.
- `cancel`: approval cancel 시 종료한다.

### Approval contract

- pending approval stage: `preprocess`.
- pending approval kind: `plan_review`.
- revise request stage: `preprocess`.
- approved path는 `approved_plan`을 executor로 넘긴다.

### Route

- `START` → `ingestion_and_profile` → `preprocess_decision`.
- decision `run_preprocess` → `planner`, `skip_preprocess` → `skip`.
- planner → approval gate.
- approval `approve` → `executor`, `revise` → `planner`, `cancel` → `cancel`.

## RAG workflow: `backend/app/orchestration/workflows/rag.py`

### Node

- `ensure_rag_index`: target source id의 index status를 확인하거나 생성한다.
- `retrieve_context`: 질문으로 `top_k=3` retrieval을 수행하고 `rag_result`를 만든다.
- `insight_synthesis`: retrieved context를 LLM summary로 합성하거나 no-evidence summary를 만든다.

### State/output

- `rag_index_status`, `rag_data_exists`, `rag_result`, `insight`가 주요 key다.
- `rag_result.evidence_summary`는 `merge_context`와 final data answer의 근거가 된다.

### 주의점

- index status가 `existing` 또는 `created`일 때만 query가 수행된다.
- retrieval 결과가 없으면 `retrieved_count=0`과 no-evidence summary를 담는다.

## Report workflow: `backend/app/orchestration/workflows/report.py`

### Node

- `report_draft`: merged context, insight, visualization summary, revision instruction으로 draft를 만든다.
- `approval_gate`: `interrupt(payload)`로 draft approval/revision/cancel을 받는다.
- `finalize`: `report_result`와 `output.type="report_answer"`를 만든다.
- `cancel`: cancel path를 정리한다.

### Approval contract

- pending approval stage: `report`.
- pending approval kind: `draft_review`.
- revise request stage: `report`.

### Route

- `START` → `report_draft` → `approval_gate`.
- approval `approve` → `finalize`, `revise` → `report_draft`, `cancel` → `cancel`.

## Visualization workflow: `backend/app/orchestration/workflows/visualization.py`

### Node

- `visualization_planner`: analysis result가 있으면 direct `analysis_generated` result를 만들고, 없으면 plan을 만든다.
- `approval_gate`: planned visualization에 대해 preview rows를 포함한 approval payload를 만들고 interrupt를 건다.
- `visualization_executor`: approved/current plan을 실행해 `visualization_result`를 만든다.
- `cancel`: cancel path를 종료한다.

### Approval contract

- pending approval stage: `visualization`.
- pending approval kind: `plan_review`.
- revise request stage: `visualization`.

### Route

- `START` → `visualization_planner`.
- planner status `analysis_generated` → `END`.
- planner status `planned` → `approval_gate`.
- 그 외 planner output은 `visualization_executor`로 간다.
- approval `approve` → `visualization_executor`, `revise` → `visualization_planner`, `cancel` → `cancel`.

## 발견한 문제점 / 확인 필요 사항

- 관찰: workflow wrapper는 얇은 조립 계층이지만 approval/resume route는 여기서 결정된다. module service만 보면 cancel/revise path를 이해할 수 없다.
- 관찰: analysis workflow는 ambiguity를 `needs_clarification`으로 main graph에 넘기지만, preprocess/visualization/report는 LangGraph interrupt 기반 approval로 사용자 개입을 처리한다.
- 리스크: `preprocess_result.output_source_id`가 생기면 이후 workflow가 `resolve_target_source_id()`를 통해 전처리 결과를 target으로 삼을 수 있다. 원본 source id만 보는 문서는 실제 흐름을 놓친다.
- 리스크: guideline workflow의 service 조립 방식은 다른 workflow와 다르다. dependency lifecycle이나 DB session scope를 판단할 때 별도 확인이 필요하다.
- 리스크: visualization은 analysis-generated direct path와 approval path가 공존한다. UI에서 항상 approval card를 기대하면 일부 정상 경로를 누락할 수 있다.
