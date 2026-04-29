# Backend orchestration 구조

`backend/app/orchestration/`은 module 사이 실행 순서, LangGraph state, approval interrupt, 최종 answer packaging, SSE-facing event를 담당한다. module business rule은 `backend/app/modules/`에 두고, 이 계층은 handoff와 shared state 계약을 연결한다.

## 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/orchestration/__init__.py` | orchestration package marker다. |
| `backend/app/orchestration/ai.py` | intent 판단, general answer, merged context 기반 data answer 생성을 담당한다. |
| `backend/app/orchestration/builder.py` | main LangGraph를 조립하고 subgraph 간 conditional edge와 terminal node를 정의한다. |
| `backend/app/orchestration/client.py` | workflow 실행 stream을 `thought`, `approval_required`, `chunk`, `done` event로 변환한다. |
| `backend/app/orchestration/dependencies.py` | workflow checkpointer, module service bundle, `AgentClient` dependency를 조립한다. |
| `backend/app/orchestration/intake_router.py` | dataset 선택 여부와 intent를 기준으로 `general_question` 또는 `data_pipeline` handoff를 만든다. |
| `backend/app/orchestration/state.py` | main/subgraph TypedDict state와 payload key 계약을 정의한다. |
| `backend/app/orchestration/utils.py` | `resolve_target_source_id()`로 원본 source와 preprocess output source 선택을 통일한다. |
| `backend/app/orchestration/tools/__init__.py` | orchestration tools package marker다. |
| `backend/app/orchestration/tools/general.py` | 임시 general search tool과 `TOOLS` list를 정의한다. |
| `backend/app/orchestration/workflows/__init__.py` | workflow wrappers package marker다. |
| `backend/app/orchestration/workflows/analysis.py` | analysis subgraph를 조립한다. |
| `backend/app/orchestration/workflows/guideline.py` | active guideline indexing/retrieval/summarization subgraph를 조립한다. |
| `backend/app/orchestration/workflows/preprocess.py` | preprocess decision/plan/approval/execution subgraph를 조립한다. |
| `backend/app/orchestration/workflows/rag.py` | dataset RAG indexing/retrieval/insight synthesis subgraph를 조립한다. |
| `backend/app/orchestration/workflows/report.py` | report draft/approval/finalize subgraph를 조립한다. |
| `backend/app/orchestration/workflows/visualization.py` | visualization plan/approval/execution subgraph를 조립한다. |

## Hotspot: `backend/app/orchestration/state.py`

### 역할

workflow 전체가 공유하는 state key와 subgraph별 payload contract를 정의한다. 기존 key rename은 frontend SSE consumer, docs, tests에 파급될 수 있다.

### 주요 payload

- `HandoffPayload`: `next_step`, `ask_preprocess`, `ask_analysis`, `ask_visualization`, `ask_report`, `ask_guideline` 등 intake route flag.
- `PreprocessResultPayload`: preprocess 적용/skip/cancel status, output source id, summary/error.
- `RagResultPayload`: retrieved chunks, context, retrieved count, evidence summary.
- `GuidelineResultPayload`: active guideline id/filename, retrieved chunks, evidence summary, status.
- `VisualizationResultPayload`: chart generation status, source id, summary, chart/artifact.
- `OutputPayload`: terminal `type`, `content`.
- `PendingApprovalPayload`: approval `stage`, `kind`, title/summary/source/plan/draft/review.
- `RevisionRequestPayload`: revise target `stage`와 instruction.

### 주요 state type

- `AgentState`: user/session/model/source/request context 공통 key.
- `IntakeRouterState`, `PreprocessGraphState`, `AnalysisGraphState`, `RagGraphState`, `GuidelineGraphState`, `VisualizationGraphState`, `ReportGraphState`: subgraph별 state 확장.
- `MainWorkflowState`: main graph가 합치는 전체 state.
- `CommonAgentState`: `AgentState` alias.

### 동적 state update 주의점

`backend/app/orchestration/workflows/analysis.py`의 `analysis_persist_result_node()`는 성공 result를 저장한 뒤 `{"analysis_result_id": result_id}`를 반환한다. 이 key는 런타임 state에 병합되는 동적 update지만, 현재 `backend/app/orchestration/state.py`의 `AnalysisGraphState` TypedDict에 정적으로 선언되어 있지는 않다. 따라서 정적 state contract를 확인할 때는 `state.py`와 subgraph node return 값을 함께 봐야 한다.

## Hotspot: `backend/app/orchestration/ai.py`

### 역할

workflow 레벨 AI 판단과 최종 answer 생성을 담당한다.

### 주요 function

- `analyze_intent(...)`: dataset이 선택된 상태에서 `IntentDecision`을 structured output으로 받아 `data_pipeline` flag를 만든다.
- `answer_general_question(...)`: dataset 없이 일반 질문에 답한다.
- `answer_data_question(...)`: `merged_context`만 근거로 data QA answer를 만든다.

### 주의점

- intent prompt는 평균/합계/그룹화/추세/상관/시각화를 analysis로 보고, 결측/형변환/정규화/인코딩/컬럼명 변경 같은 데이터 변경을 preprocess로 본다.
- `answer_data_question()`은 `merged_context` 밖의 정보를 근거로 쓰지 말라는 system prompt를 사용한다.

## Hotspot: `backend/app/orchestration/builder.py`

### 역할

main graph의 node, edge, terminal, context merge를 정의한다.

### Main node

- `intake_flow`: `build_intake_router_workflow()` subgraph.
- `general_question_terminal`: dataset 없이 general answer를 만든다.
- `clarification_terminal`: analysis ambiguity 질문을 output으로 만든다.
- `preprocess_flow`: preprocess subgraph.
- `analysis_flow`: analysis subgraph.
- `rag_flow`: dataset RAG subgraph.
- `guideline_flow`: guideline subgraph.
- `visualization_flow`: visualization subgraph.
- `merge_context`: downstream answer/report에 넘길 `merged_context`를 만든다.
- `data_qa_terminal`: 최종 data answer를 만든다.
- `report_flow`: report subgraph.

### Route summary

- `START` → `intake_flow`.
- intake 결과 `general_question` → `general_question_terminal`, `data_pipeline` → `preprocess_flow`.
- preprocess 결과 `analysis` → `analysis_flow`, `rag` → `rag_flow`, `cancelled` → `END`.
- analysis 결과 `guideline`/`visualization`/`merge_context`/`clarification`/`fail`로 분기한다.
- rag 결과 `guideline`/`visualization`/`merge_context`로 분기한다.
- guideline 결과 `visualization` 또는 `merge_context`로 분기한다.
- visualization 결과 `merge_context` 또는 `cancelled`로 분기한다.
- merge context 이후 `report` → `report_flow`, 그 외 `data_qa` → `data_qa_terminal`.

### `merge_context` payload

`merge_context_node()`는 `applied_steps`, `request_context`, `request_flags`, `preprocess_result`, `rag_result`, `guideline_index_status`, `guideline_result`, `guideline_context`, `insight`, `analysis_plan`, `analysis_result`, `visualization_result`를 가능한 경우 모아 `merged_context`를 만든다.

## Hotspot: `backend/app/orchestration/client.py`

### 역할

Compiled workflow를 실행하고 LangGraph snapshot을 사용자-facing stream event로 바꾼다.

### 주요 method

- `astream_with_trace(...)`: 새 질문 또는 resume payload를 workflow에 넣고 event stream을 만든다.
- `get_pending_approval(run_id)`: checkpointer snapshot interrupt에서 pending approval을 읽는다.
- `_build_state(...)`: question/context/session/run/model/dataset/source id를 초기 state로 만든다.
- `_build_config(...)`: `thread_id`를 `run_id`, `session_id`, `default` 순서로 선택한다.
- `_extract_interrupt_payload(...)`: snapshot의 `__interrupt__`에서 approval payload를 읽는다.
- `_collect_thought_steps(...)`: state 변화에 맞는 phase/message/status thought step을 만든다.

### Event output

- `thought`: phase/status progress.
- `approval_required`: pending approval payload와 thought steps.
- `chunk`: final answer를 24자 단위로 나눈 delta.
- `done`: answer, thought steps, output type, optional output, optional preprocess result, generated visualization result.

## Hotspot: `backend/app/orchestration/dependencies.py`

### 역할

FastAPI dependency로 `AgentClient`와 workflow runtime factory를 만든다.

### 주요 function/class

- `WorkflowServices`: analysis/preprocess/EDA/RAG/visualization/report service bundle.
- `get_workflow_checkpointer()`: process-local `InMemorySaver`를 lru cache로 제공한다.
- `build_orchestration_services(db, agent)`: dataset repository/reader를 공유해 module services를 조립한다.
- `build_agent_client(db)`: runtime factory와 checkpointer를 가진 `AgentClient`를 만든다.
- `get_agent_client(...)`: FastAPI dependency entrypoint다.

### 주의점

- workflow runtime은 `AgentClient` 실행 시점마다 service bundle과 compiled main workflow를 만든다.
- `InMemorySaver` 기반 pending approval은 process memory에 의존한다.

## Hotspot: `backend/app/orchestration/intake_router.py`

### 역할

초기 요청이 dataset-selected data pipeline인지, dataset 없이 general answer인지 결정한다.

### 동작

- `source_id`가 없으면 `general_question_handoff` node가 `handoff.next_step="general_question"`을 반환한다.
- `source_id`가 있으면 `intent_classification` node가 `analyze_intent()`를 호출하고 `data_pipeline_handoff`로 넘긴다.
- `data_pipeline_handoff`는 `IntentDecision` flag를 `handoff`에 복사하고 `next_step="data_pipeline"`을 설정한다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: `backend/app/orchestration/client.py`의 최초 thought phase는 `analysis`로 표시되지만 실제로는 intake routing 전 단계다. frontend 표시와 문서 해석에서 phase label 의미를 혼동하지 않아야 한다.
- 관찰: `backend/app/orchestration/dependencies.py`에는 dataset builder import가 중복되어 있다. 동작 문제로 단정할 수는 없지만 문서상 service 조립 위치를 볼 때 노이즈가 된다.
- 관찰: guideline workflow는 일부 service/repository 조립을 `backend/app/orchestration/dependencies.py` service bundle 밖에서 수행한다. module-orchestration 책임 경계 확인이 필요한 지점이다.
- 리스크: `state.py` key rename은 main builder, client, chat service, frontend SSE consumer, architecture docs에 동시에 영향을 준다. 기존 key는 additive 방식으로 다루는 것이 현재 문서 기준과 맞다.
