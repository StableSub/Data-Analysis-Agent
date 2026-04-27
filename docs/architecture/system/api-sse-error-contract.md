# API / SSE 오류 계약

## 문서 목적

이 문서는 현재 채팅 스트리밍 경로에서 프론트엔드가 기대하는 SSE 이벤트와 오류 처리 계약을 정리한다.
기준 코드는 `backend/app/modules/chat/router.py`, `backend/app/modules/chat/service.py`, `backend/app/orchestration/client.py`, `frontend/src/app/hooks/useAnalysisPipeline.ts`다.

## 범위

- `POST /chats/stream`
- `POST /chats/{session_id}/runs/{run_id}/resume`
- `GET /chats/{session_id}/runs/{run_id}/pending-approval`
- 스트리밍 중 `error` 이벤트

## 전송 형식

백엔드는 `_format_sse()`에서 아래 형식으로 이벤트를 직렬화한다.

```text
event: <name>
data: <json>
```

응답 헤더는 다음 값을 사용한다.

- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`
- `Content-Type: text/event-stream`

## 이벤트 순서 계약

### 질문 시작 (`POST /chats/stream`)

정상 흐름의 기본 순서:

1. `session`
2. 0개 이상의 `thought`
3. `chunk` 반복 **또는** `approval_required`
4. 승인 없는 경우 최종 `done`

### 승인 후 재개 (`POST /chats/{session_id}/runs/{run_id}/resume`)

기본 순서:

1. `session`
2. 0개 이상의 `thought`
3. `chunk` 반복 **또는** 다시 `approval_required`
4. 최종 `done`

## 이벤트별 payload

### `session`

```json
{ "session_id": 123, "run_id": "<hex>" }
```

- `session_id`는 정수다.
- `run_id`는 문자열이다.
- 프론트엔드는 이 값을 이후 `pending-approval`, `resume`, `history` 복원 키로 사용한다.

### `thought`

```json
{ "phase": "analysis", "message": "...", "status": "completed|active" }
```

- `phase`, `message`는 문자열이다.
- 프론트엔드는 진행 로그와 단계 UI를 갱신한다.

### `chunk`

```json
{ "delta": "부분 응답" }
```

- `delta`는 누적해서 최종 answer를 구성한다.

### `approval_required`

```json
{
  "session_id": 123,
  "run_id": "<hex>",
  "pending_approval": {
    "stage": "preprocess|visualization|report",
    "kind": "plan_review|draft_review",
    "title": "...",
    "summary": "...",
    "source_id": "...",
    "plan": {},
    "draft": "",
    "review": {}
  },
  "thought_steps": []
}
```

현재 stage 의미:

- `preprocess`: 전처리 계획 승인 대기
- `visualization`: 시각화 계획 승인 대기
- `report`: 리포트 초안 검토 대기

프론트엔드 동작:

- 상태를 `needs-user`로 전환
- `pendingApproval`을 저장
- `resumeRun(decision, stage, instruction)` 호출 전까지 스트림 종료로 간주

### `done`

```json
{
  "answer": "최종 응답",
  "session_id": 123,
  "run_id": "<hex>",
  "thought_steps": [],
  "preprocess_result": {},
  "visualization_result": {},
  "output_type": "...",
  "output": {}
}
```

- `answer`가 비어 있으면 backend가 `응답을 생성하지 못했습니다.`로 보정한다.
- `visualization_result`는 status가 `generated`일 때만 포함될 수 있다.
- `output`은 orchestration 최종 payload를 전달할 때만 포함된다.

### `error`

```json
{ "message": "오류 메시지" }
```

현재 구현 특성:

- 구조화된 `code`, `stage`, `retryable` 필드는 없다.
- 예외가 발생하면 router가 `str(exc)`만 담아 `error` 이벤트를 보낸다.
- 프론트엔드는 이 이벤트를 받으면 `Error`를 throw하고 `state="error"` 경로로 이동한다.

## HTTP 오류 계약

### `GET /chats/{session_id}/runs/{run_id}/pending-approval`

- pending approval이 없으면 `404` + `detail="pending approval not found"`

### `GET /chats/{session_id}/history`

- session이 없으면 `404` + `detail="세션을 찾을 수 없습니다."`

### `DELETE /chats/{session_id}`

- session이 없으면 `404` + `detail="세션을 찾을 수 없습니다."`
- 존재하면 `204 No Content`

## 프론트엔드 의존 포인트

`frontend/src/app/hooks/useAnalysisPipeline.ts`는 다음 가정을 둔다.

- `session` 이벤트가 먼저 와서 `session_id`, `run_id`를 세팅한다
- `approval_required.pending_approval`은 parse 가능한 객체다
- `done.answer` 또는 누적 `chunk`로 최종 답을 복원할 수 있다
- `error.message`는 사용자에게 보여줄 수 있는 문자열이다

따라서 SSE 이름이나 핵심 필드명(`session_id`, `run_id`, `pending_approval`, `delta`, `answer`, `message`)을 바꾸면 프론트엔드와 문서를 함께 수정해야 한다.

## 검토 체크리스트

- [ ] 새 SSE event를 추가했다면 프론트엔드 parser를 함께 수정했는가
- [ ] 오류 payload에 새 필드를 추가했다면 backward compatibility를 확인했는가
- [ ] `approval_required` shape 변경 시 `pending-approval` GET 응답도 같은 shape를 유지하는가
- [ ] 발표에서 “오류 분류 체계”를 말할 때 현재는 message 중심 계약임을 분명히 했는가

## 발표용 framing

현재 시스템의 장점은 SSE로 **session → thought → approval/done** 흐름이 명확하다는 점이다.
반면 오류 계약은 아직 단순 메시지 수준이므로, 발표에서는 “구조화된 error code는 향후 보강 항목”이라고 설명하는 것이 정확하다.
