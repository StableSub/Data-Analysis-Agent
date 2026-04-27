# 채팅 SSE 및 오류 계약

## 문서 목적

이 문서는 현재 채팅 실행 경로의 SSE 이벤트 형식, 승인 대기 payload, 종료 payload, 오류 처리 방식을 실제 코드 기준으로 정리한다.
기준 구현은 `backend/app/modules/chat/router.py`, `backend/app/modules/chat/service.py`, `backend/app/modules/chat/schemas.py`, `frontend/src/app/hooks/useAnalysisPipeline.ts`, `frontend/src/lib/api.ts`다.

## 적용 범위

- `POST /chats/stream`
- `POST /chats/{session_id}/runs/{run_id}/resume`
- `GET /chats/{session_id}/runs/{run_id}/pending-approval`
- 프론트엔드 Workbench의 SSE 소비 계약

## 서버 측 SSE 형식

`backend/app/modules/chat/router.py`의 `_format_sse(...)`는 모든 스트리밍 이벤트를 아래 형식으로 직렬화한다.

```text
event: <event-name>
data: <json>

```

- `event`는 문자열 이벤트 이름이다.
- `data`는 `json.dumps(..., ensure_ascii=False)` 결과다.
- 응답 `media_type`은 `text/event-stream`이다.
- 공통 헤더는 `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`다.

## 이벤트 생성 위치

`backend/app/modules/chat/service.py`의 `_relay_agent_events(...)`가 내부 agent event를 SSE-facing 이벤트로 변환한다.

| 내부 이벤트 | 외부 SSE 이벤트 | 생성 위치 | 핵심 payload |
| --- | --- | --- | --- |
| `thought` | `thought` | `_relay_agent_events(...)` | `phase`, `message`, `status` |
| `approval_required` | `approval_required` | `_relay_agent_events(...)` | `session_id`, `run_id`, `pending_approval`, `thought_steps` |
| `chunk` | `chunk` | `_relay_agent_events(...)` | `delta` |
| `done` | `done` | `_relay_agent_events(...)` 종료 시점 | `answer`, `session_id`, `run_id`, `thought_steps`, 선택적 결과 필드 |
| 예외 | `error` | `router.py`의 `event_generator()` 예외 처리 | `message` |

또한 `ask_stream(...)`와 `resume_run_stream(...)`는 본격적인 agent stream 전에 항상 `session` 이벤트를 먼저 내보낸다.

## 이벤트별 payload 계약

### 1. `session`

생성 위치:
- `backend/app/modules/chat/service.py::ask_stream`
- `backend/app/modules/chat/service.py::resume_run_stream`

payload:

```json
{
  "session_id": 1,
  "run_id": "<uuid-hex>"
}
```

용도:
- 프론트엔드가 현재 세션과 실행 식별자를 먼저 고정하는 데 사용한다.

### 2. `thought`

생성 위치:
- `backend/app/modules/chat/service.py::_relay_agent_events`

payload 필드:
- `phase`
- `message`
- `status`

프론트엔드는 `frontend/src/app/hooks/useAnalysisPipeline.ts`에서 `parseThoughtStep(...)`로 파싱해 타임라인에 추가한다.

### 3. `chunk`

생성 위치:
- `backend/app/modules/chat/service.py::_relay_agent_events`

payload 필드:
- `delta`

프론트엔드는 `delta` 문자열을 이어 붙여 streaming answer를 만든다.

### 4. `approval_required`

생성 위치:
- `backend/app/modules/chat/service.py::_relay_agent_events`

payload 필드:
- `session_id`
- `run_id`
- `pending_approval`
- `thought_steps`

`pending_approval`의 구조는 `backend/app/modules/chat/schemas.py::PendingApproval` 기준으로 아래 셋 중 하나다.

#### preprocess 승인

```json
{
  "stage": "preprocess",
  "kind": "plan_review",
  "title": "...",
  "summary": "...",
  "source_id": "...",
  "plan": {}
}
```

#### visualization 승인

```json
{
  "stage": "visualization",
  "kind": "plan_review",
  "title": "...",
  "summary": "...",
  "source_id": "...",
  "plan": {}
}
```

#### report 승인

```json
{
  "stage": "report",
  "kind": "draft_review",
  "title": "...",
  "summary": "...",
  "source_id": "...",
  "draft": "...",
  "review": {}
}
```

프론트엔드 동작:
- `frontend/src/app/hooks/useAnalysisPipeline.ts`는 `approval_required`를 받으면 `parsePendingApproval(...)`로 해석한다.
- payload 해석 실패 시 `Error("승인 대기 payload를 해석할 수 없습니다.")`를 던지고 오류 상태로 전환한다.
- 성공하면 `state="needs-user"`로 바꾸고 approval card를 띄운다.

### 5. `done`

생성 위치:
- `backend/app/modules/chat/service.py::_relay_agent_events`

기본 payload 필드:
- `answer`
- `session_id`
- `run_id`
- `thought_steps`
- `preprocess_result`

선택적 필드:
- `visualization_result`
- `output_type`
- `output`

세부 규칙:
- 내부 `done` 이벤트에 `answer`가 없으면 누적한 `chunk`를 합쳐 최종 답변으로 사용한다.
- 최종 답변이 비어 있으면 `