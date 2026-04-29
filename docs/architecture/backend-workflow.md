# Backend end-to-end workflow

이 문서는 `backend/app/main.py`에서 mounted router로 시작해 `/chats/stream` SSE 응답이 끝나는 전체 backend workflow를 코드 기준으로 정리한다. 세부 파일 카탈로그는 [core](./core/README.md), [modules](./modules/README.md), [orchestration](./orchestration/README.md)를 함께 본다.

## 1. FastAPI app startup and router mount

진입 파일은 `backend/app/main.py`다.

- `load_dotenv()`로 환경 변수를 로딩한다.
- `FastAPI()` app을 만든다.
- CORS origin은 `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173`, `http://127.0.0.1:5173`를 허용한다.
- startup handler `on_startup()`에서 `Base.metadata.create_all(bind=engine)`를 실행한다.
- 다음 router를 직접 mount한다.

| router import | 실제 prefix | 역할 |
|---|---:|---|
| `backend/app/modules/datasets/router.py` | `/datasets` | dataset upload/list/detail/delete/sample |
| `backend/app/modules/eda/router.py` | `/eda` | profile/EDA/statistics/insight |
| `backend/app/modules/chat/router.py` | `/chats` | chat session, SSE, resume, history |
| `backend/app/modules/analysis/router.py` | `/analysis` | direct analysis run/result lookup |
| `backend/app/modules/visualization/router.py` | `/vizualization` | manual/from-analysis visualization |
| `backend/app/modules/rag/router.py` | `/rag` | RAG query/source delete |
| `backend/app/modules/export/router.py` | `/export` | CSV export |
| `backend/app/modules/guidelines/router.py` | `/guidelines` | guideline upload/list/activate/delete |
| `backend/app/modules/preprocess/router.py` | `/preprocess` | direct preprocess apply |
| `backend/app/modules/reports/router.py` | `/report` | report create/list/get |

## 2. Chat request entry

대화형 runtime은 `backend/app/modules/chat/router.py`에서 시작한다.

### Streaming path

1. `POST /chats/stream`이 `ChatRequest`를 받는다.
2. route 내부 `event_generator()`가 `ChatService.ask_stream()`을 순회한다.
3. 각 service event는 `_format_sse()`로 `event: ...`, `data: ...` SSE chunk가 된다.
4. 예외가 발생하면 SSE `error` event로 `{message}`를 반환한다.

### Non-stream path

1. `POST /chats/`가 `ChatService.ask()`를 호출한다.
2. `ask()`는 내부적으로 `ask_stream()`을 끝까지 소비한다.
3. `done`이 있으면 `ChatResponse`를 만들고, `approval_required`가 있으면 pending approval이 포함된 `ChatResponse`를 만든다.

### Resume path

1. `POST /chats/{session_id}/runs/{run_id}/resume`가 `ResumeRunRequest`를 받는다.
2. `ChatService.resume_run_stream()`이 `AgentClient.astream_with_trace(resume={decision, stage, instruction})`를 호출한다.
3. LangGraph interrupt 지점이 resume decision에 따라 approve/revise/cancel 경로로 진행된다.

## 3. ChatService session and AgentClient handoff

`backend/app/modules/chat/service.py`가 session/message와 agent stream relay를 담당한다.

1. `_get_or_create_session()`으로 session을 찾거나 만든다.
2. `source_id`가 있으면 `DataSourceRepository.get_by_source_id(source_id)`로 selected dataset model을 찾는다.
3. user message를 `ChatRepository.append_message()`로 저장한다.
4. `run_id = uuid.uuid4().hex`를 만들고 `session` SSE event를 먼저 보낸다.
5. `AgentClient.astream_with_trace(session_id, run_id, question, dataset, model_id)`를 호출한다.
6. `_relay_agent_events()`가 agent event를 chat SSE event로 변환한다.
7. final answer가 생기면 assistant message를 저장하고 `done` event를 보낸다.

## 4. AgentClient initial state and thread config

`backend/app/orchestration/client.py`의 `AgentClient`가 workflow runtime을 실행한다.

### Initial state

`_build_state()`는 새 질문을 다음 key로 변환한다.

- `user_input`: 질문 text.
- `request_context`: optional context text.
- `session_id`: chat session id string.
- `run_id`: run id string.
- `model_id`: request model id 또는 default model.
- `dataset_id`: selected dataset DB id.
- `source_id`: selected dataset source id.

질문이 비어 있으면 workflow를 실행하지 않고 early answer `질문을 입력해 주세요.`를 `chunk`와 `done`으로 반환한다.

### Config

`_build_config()`는 LangGraph `thread_id`를 `run_id`, `session_id`, `default` 순서로 정한다. pending approval 조회도 같은 run id 기반 checkpointer state를 사용한다.

## 5. Intake routing

`backend/app/orchestration/intake_router.py`가 coarse route를 결정한다.

- `source_id`가 없으면 `general_question_handoff`가 `handoff.next_step="general_question"`을 반환한다.
- `source_id`가 있으면 `intent_classification`이 `analyze_intent()`를 호출한다.
- `data_pipeline_handoff`는 `IntentDecision` flag를 `handoff`에 복사하고 `next_step="data_pipeline"`을 설정한다.

`IntentDecision`의 주요 flag:

- `ask_preprocess`
- `ask_analysis`
- `ask_visualization`
- `ask_report`
- `ask_guideline`

## 6. Main workflow graph

`backend/app/orchestration/builder.py`의 `build_main_workflow()`가 main LangGraph를 조립한다.

### High-level route

```text
START
  -> intake_flow
     -> general_question_terminal -> END
     -> preprocess_flow
        -> analysis_flow | rag_flow | END(cancelled)
           -> guideline_flow | visualization_flow | merge_context | clarification_terminal | END(fail)
        -> rag_flow
           -> guideline_flow | visualization_flow | merge_context
        -> guideline_flow
           -> visualization_flow | merge_context
        -> visualization_flow
           -> merge_context | END(cancelled)
        -> merge_context
           -> report_flow -> END
           -> data_qa_terminal -> END
```

### Terminal output type

| terminal/path | `output.type` | 생성 위치 |
|---|---|---|
| general question | `general_question` | `general_question_terminal` |
| analysis clarification | `clarification` | `clarification_terminal` |
| preprocess/visualization/report cancel | `cancelled` | 해당 workflow approval cancel path |
| data answer | `data_qa` | `data_qa_terminal` |
| report answer | `report_answer` | report workflow finalize node |

## 7. Subgraph responsibilities

### Preprocess subgraph

파일: `backend/app/orchestration/workflows/preprocess.py`.

- profile을 만들고 preprocess 필요 여부를 판단한다.
- 필요하면 plan을 만들고 `pending_approval.stage="preprocess"`, `kind="plan_review"`로 interrupt를 건다.
- approve면 plan을 적용하고 `preprocess_result`를 만든다.
- skip이면 `preprocess_result.status="skipped"`를 반환한다.
- cancel이면 output type `cancelled`로 종료된다.

### Analysis subgraph

파일: `backend/app/orchestration/workflows/analysis.py`.

- dataset metadata, question understanding, column grounding, plan draft, final plan을 만든다.
- ambiguity가 남으면 `final_status="needs_clarification"`와 `clarification_question`을 반환한다.
- code generation loop, sandbox execution, validation, persistence를 수행한다.
- 실패하면 `final_status="fail"`, 성공하면 `analysis_result`와 저장 id를 반환한다.

### RAG subgraph

파일: `backend/app/orchestration/workflows/rag.py`.

- dataset index status를 확인하거나 생성한다.
- query context를 검색해 `rag_result.retrieved_chunks`, `retrieved_count`, `context`를 만든다.
- evidence가 있으면 insight를 합성하고, 없으면 no-evidence summary를 만든다.

### Guideline subgraph

파일: `backend/app/orchestration/workflows/guideline.py`.

- active guideline source를 확인한다.
- guideline index/retrieval을 수행한다.
- `guideline_result`와 `guideline_index_status`를 main state에 올린다.

### Visualization subgraph

파일: `backend/app/orchestration/workflows/visualization.py`.

- `analysis_result`와 `analysis_plan`이 있으면 `analysis_generated` 경로로 direct visualization result를 만든다.
- 그렇지 않으면 visualization plan을 만들고 `pending_approval.stage="visualization"`, `kind="plan_review"`로 interrupt를 건다.
- approve면 executor가 `visualization_result`를 만든다.
- cancel이면 output type `cancelled`로 종료된다.

### Report subgraph

파일: `backend/app/orchestration/workflows/report.py`.

- `merged_context`, insight, visualization summary로 report draft를 만든다.
- `pending_approval.stage="report"`, `kind="draft_review"`로 interrupt를 건다.
- approve면 `output.type="report_answer"`와 report content를 만든다.

## 8. Context merge and final answer

`merge_context_node()`는 다음 정보를 가능한 경우 `merged_context`로 모은다.

- `applied_steps`
- `request_context`
- `request_flags`
- `preprocess_result`
- `rag_result`
- `guideline_index_status`
- `guideline_result`
- `guideline_context`
- `insight`
- `analysis_plan`
- `analysis_result`
- `visualization_result`

`data_qa_terminal()`은 `answer_data_question()`을 호출해 `merged_context`만 근거로 final answer를 생성한다. report 요청이면 `merge_context` 이후 `report_flow`가 draft approval/finalize를 담당한다.

## 9. Stream output and done event

`AgentClient.astream_with_trace()`는 workflow snapshot을 다음 event로 바꾼다.

- `thought`: phase/message/status progress.
- `approval_required`: `pending_approval`과 현재 thought steps.
- `chunk`: final answer text를 24자 단위로 나눈 delta.
- `done`: final answer와 output metadata.

`AgentClient` 내부 `done` event의 주요 key:

- `answer`
- `thought_steps`
- `output_type`
- `output`: `final_state["output"]`이 dict일 때만 포함된다.
- `preprocess_result`: `final_state["preprocess_result"]`가 dict일 때만 포함된다.
- `visualization_result`는 status가 `generated`일 때만 포함된다.

`ChatService._relay_agent_events()`는 내부 event를 SSE response data로 바꾼다. 최종 SSE `done` data에는 항상 `answer`, `session_id`, `run_id`, `thought_steps`, `preprocess_result` key가 있으며, `preprocess_result` 값은 내부 event에서 dict가 오지 않으면 `None`일 수 있다. `output_type`, `output`, `visualization_result`는 값이 있을 때만 추가된다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: 현재 backend에는 별도 중앙 API registry가 없고 `backend/app/main.py`에서 router를 직접 include한다. route 전체를 보려면 main과 각 module router를 함께 확인해야 한다.
- 관찰: main graph는 dataset pipeline에서 항상 `preprocess_flow`를 먼저 통과한다. 실제 preprocess가 필요 없으면 subgraph 내부에서 skip result를 반환한 뒤 analysis 또는 rag로 넘어간다.
- 관찰: `backend/app/orchestration/client.py`와 `backend/app/modules/chat/service.py`가 함께 최종 SSE `done` payload를 만든다. 한 파일만 보면 frontend contract가 완성되지 않는다.
- 리스크: `InMemorySaver` checkpointer는 approval resume 상태를 process memory에 보관한다. process 재시작이나 multi-process 환경에서 pending approval 처리 방식은 별도 확인이 필요하다.
- 리스크: 새 문서 위치는 `docs/system/*`, `docs/architecture/modules/*`, `docs/architecture/orchestration/*`로 나뉜다. 경로를 바꾸는 후속 작업은 docs harness와 active context 문서를 함께 갱신해야 한다.
