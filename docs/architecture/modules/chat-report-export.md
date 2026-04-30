# Chat, report, results modules

이 문서는 backend runtime 진입점인 chat module과, 최종 산출물 저장·조회·내보내기를 담당하는 report/results module을 정리한다. 사용자 질문의 end-to-end 흐름은 `backend/app/modules/chat/service.py`에서 `backend/app/orchestration/client.py`로 넘어간 뒤 다시 SSE `done` event로 돌아온다.

## `chat/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/chat/__init__.py` | chat package marker다. |
| `backend/app/modules/chat/dependencies.py` | `ChatRepository`, `ChatService` dependency를 만든다. |
| `backend/app/modules/chat/models.py` | `ChatSession`, `ChatMessage` SQLAlchemy model을 정의한다. |
| `backend/app/modules/chat/repository.py` | chat session/message 생성, 조회, 삭제 repository다. |
| `backend/app/modules/chat/router.py` | `APIRouter(prefix="/chats")`로 sync ask, SSE stream, resume, pending approval, history, delete route를 제공한다. |
| `backend/app/modules/chat/schemas.py` | `ChatRequest`, `ChatResponse`, `ChatThoughtStep`, `PendingApproval`, `ResumeRunRequest`, history/approval response schema를 정의한다. |
| `backend/app/modules/chat/service.py` | session 생성, user/assistant message 저장, `AgentClient` stream relay, final SSE payload packaging을 담당한다. |

## `reports/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/reports/__init__.py` | reports package marker다. |
| `backend/app/modules/reports/ai.py` | report draft와 summary 생성을 위한 LLM prompt/call을 담당한다. |
| `backend/app/modules/reports/dependencies.py` | `ReportRepository`, `ReportService` dependency builder/getter를 제공한다. |
| `backend/app/modules/reports/models.py` | `Report` SQLAlchemy model을 정의한다. |
| `backend/app/modules/reports/repository.py` | report create/get/list persistence를 담당한다. |
| `backend/app/modules/reports/service.py` | report draft 생성, dataset metrics 구성, summary 생성, 저장 use case를 담당한다. |

## `results/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/results/models.py` | `AnalysisResult`, `ChartResult`, `ViewSnapshot` SQLAlchemy model을 정의한다. |
| `backend/app/modules/results/repository.py` | analysis result 저장/조회, chart data update, model dump/result JSON build를 담당한다. |

## Public route 요약

### `backend/app/modules/chat/router.py`

- `POST /chats/`: streaming이 아닌 chat ask API다. 내부적으로 stream을 소비해 final response를 만든다.
- `POST /chats/stream`: SSE로 `session`, `thought`, `approval_required`, `chunk`, `done`, `error` event를 낸다.
- `POST /chats/{session_id}/runs/{run_id}/resume`: approval interrupt 이후 approve/revise/cancel 결정을 resume한다.
- `GET /chats/{session_id}/runs/{run_id}/pending-approval`: checkpointer snapshot에서 pending approval을 조회한다.
- `GET /chats/{session_id}/history`: session history를 조회한다.
- `DELETE /chats/{session_id}`: session을 삭제한다.


## Hotspot: `backend/app/modules/chat/router.py`

### 역할

FastAPI route와 SSE formatting을 담당한다. `ask_chat_stream()`과 `resume_chat_run()`은 내부 async generator에서 service event를 SSE string으로 변환한다.

### 주요 function

- `_format_sse(event, data)`: `event: ...\ndata: ...\n\n` 형태의 SSE chunk를 만든다.
- `ask_chat(...)`: `ChatService.ask()`를 호출해 non-stream response를 반환한다.
- `ask_chat_stream(...)`: `ChatService.ask_stream()` event를 `StreamingResponse`로 감싼다.
- `resume_chat_run(...)`: `ChatService.resume_run_stream()` event를 `StreamingResponse`로 감싼다.
- `get_pending_approval(...)`, `get_history(...)`, `delete_chat(...)`: session/run 보조 API다.

### 주의점

- stream/resume generator는 예외를 잡아 SSE `error` event로 `{"message": str(exc)}`를 보낸다.
- SSE payload shape는 frontend pipeline state와 직접 연결되므로 event 이름과 data key를 정확히 유지해야 한다.

## Hotspot: `backend/app/modules/chat/service.py`

### 역할

`ChatService`는 session lifecycle과 agent stream relay를 함께 담당한다. backend 전체 workflow의 사용자-facing entry service다.

### 주요 method

- `ask(...)`: `ask_stream()`을 내부 소비해 `ChatResponse`를 만든다. approval이 필요한 경우 answer 없이 pending approval을 포함한다.
- `ask_stream(...)`: session 생성/조회, selected dataset resolve, user message 저장, run id 생성, `AgentClient.astream_with_trace()` 호출을 수행한다.
- `resume_run_stream(...)`: 기존 run id에 대해 `Command(resume=...)` payload로 workflow를 재개한다.
- `get_pending_approval(...)`: `AgentClient.get_pending_approval()` 결과를 response schema로 감싼다.
- `_relay_agent_events(...)`: agent event를 chat SSE event로 변환하고 final answer를 assistant message로 저장한다.

### SSE event packaging

- `session`: `{session_id, run_id}`.
- `thought`: `{phase, message, status}`.
- `approval_required`: `{session_id, run_id, pending_approval, thought_steps}`.
- `chunk`: `{delta}`.
- `done`: `{answer, session_id, run_id, thought_steps, preprocess_result, visualization_result?, output_type?, output?}`.

### 주의점

- `done` payload에는 `preprocess_result` key가 항상 포함되며 값이 `None`일 수 있다.
- `visualization_result`, `output_type`, `output`은 agent done event에 있을 때만 추가된다.
- assistant message 저장은 stream이 끝난 뒤 final answer 기준으로 수행된다.

## Hotspot: `backend/app/modules/reports/service.py`

### 역할

`ReportService`는 dataset metrics, insight summary, visualization summary를 묶어 report draft/summary를 만들고 저장한다.

### 주요 책임

- `build_metrics_for_source(...)`: dataset row/column/quality metric을 만든다.
- `build_report_draft(...)`: question/context 기반 report draft를 생성한다.
- `generate_summary(...)`, `create_report_from_request(...)`, `create_report(...)`, `get_report(...)`, `list_reports(...)`: report 생성·조회 use case다.

### 연결 관계

- `backend/app/orchestration/workflows/report.py`에서 report draft approval/finalize 흐름에 사용된다.

## Hotspot: `backend/app/modules/results/repository.py`

### 역할

analysis result persistence와 downstream visualization 조회의 기준 repository다.

### 주요 책임

- `create_analysis_result(...)`: analysis result, chart result, view snapshot을 저장한다.
- `get_analysis_result_data(...)`: 저장된 result JSON을 API/export에서 쓰기 좋은 형태로 읽는다.
- `get_analysis_result(...)`: model 객체를 조회한다.
- `update_chart_data(...)`: chart data를 갱신한다.
- `_build_result_json(...)`: DB model과 payload를 result JSON 형태로 구성한다.

### 연결 관계

- `backend/app/modules/analysis/service.py`가 성공 result 저장 시 사용한다.
- `backend/app/modules/visualization/service.py`가 from-analysis chart 생성에서 저장 결과를 읽는다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: chat module은 단순 CRUD가 아니라 orchestration runtime 진입점이다. `backend/app/modules/chat/service.py`를 보지 않고 backend workflow를 이해하면 SSE/resume/approval 흐름이 빠진다.
- 관찰: `backend/app/modules/chat/router.py`의 stream error event는 `message`만 포함한다. stage별 error context가 필요한 디버깅에서는 server log와 workflow state를 같이 확인해야 한다.
- 리스크: `done` event payload는 `AgentClient` output과 `ChatService` relay가 결합해 만들어진다. 두 파일 중 하나만 보고 frontend contract를 판단하면 누락이 생길 수 있다.
- 리스크: `results/`는 public router가 없지만 analysis/visualization이 공유하는 persistence seam이다. result JSON shape 변경은 여러 module에 파급된다.
