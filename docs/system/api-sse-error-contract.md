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

요청한 `source_id`가 존재하지 않고 기존 `session_id`도 없는 경우는 새 빈 세션을 만들지 않고 `error` 이벤트만 반환한다.

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
  "trace_id": "<hex>",
  "thought_steps": [],
  "preprocess_result": {},
  "visualization_result": {},
  "output_type": "...",
  "output": {},
  "status": "success|limited|unanswerable|failed|cancelled",
  "error_stage": "preprocess",
  "error_message": "오류 메시지",
  "retryable": true,
  "evidence_package": {
    "source_id": "...",
    "filename": "...",
    "used_columns": [],
    "analysis_status": "success|fail|missing",
    "rag_retrieved_count": 0,
    "guideline_retrieved_count": 0,
    "preprocess_status": "skipped|applied|failed|cancelled",
    "warnings": []
  },
  "answer_quality": {
    "answerable": true,
    "status": "answerable|limited|unanswerable",
    "abstain_reason": "...",
    "warnings": []
  }
}
```

- `answer`가 비어 있으면 backend가 `응답을 생성하지 못했습니다.`로 보정한다.
- `output_type`은 사용자-facing terminal type이다. fast path로 계산되더라도 최상위 done event는 `data_qa`로 정규화하고, 내부 fast-path 세부 타입은 `output.type`에 남길 수 있다.
- `visualization_result`는 status가 `generated`일 때만 포함될 수 있다.
- `output`은 orchestration 최종 payload를 전달할 때만 포함된다.
- `status`는 `ChatService`가 최종 payload에서 계산하는 terminal 상태다. 성공은 `success`, 근거 제한은 `limited`/`unanswerable`, 실패/취소는 `failed`/`cancelled`로 표현한다.
- `error_stage`, `error_message`, `retryable`은 실패 또는 취소 성격의 `done` payload에서만 포함될 수 있다.
- `evidence_package`, `answer_quality`는 optional metadata다. 같은 값이 `output.evidence_package`, `output.answer_quality`에도 들어갈 수 있다.

### `error`

```json
{
  "session_id": 123,
  "run_id": "<hex>",
  "trace_id": "<hex>",
  "thought_steps": [],
  "answer": "사용자에게 보여줄 오류 응답",
  "message": "사용자에게 보여줄 오류 응답",
  "status": "failed",
  "stage": "analysis_repair_failed",
  "error_stage": "analysis_repair_failed",
  "error_message": "분석 코드를 자동으로 수정했지만 실행 가능한 형태로 만들지 못했습니다. 질문 범위나 기준 컬럼을 좁혀 다시 실행해 주세요.",
  "error_code": "analysis_repair_failed",
  "retryable": true,
  "public_error": {
    "stage": "analysis_repair_failed",
    "error_stage": "analysis_repair_failed",
    "error_code": "analysis_repair_failed",
    "retryable": true,
    "message": "분석 코드를 자동으로 수정했지만 실행 가능한 형태로 만들지 못했습니다. 질문 범위나 기준 컬럼을 좁혀 다시 실행해 주세요.",
    "error_message": "분석 코드를 자동으로 수정했지만 실행 가능한 형태로 만들지 못했습니다. 질문 범위나 기준 컬럼을 좁혀 다시 실행해 주세요.",
    "output_type": "analysis_failed"
  },
  "output_type": "analysis_failed",
  "output": {},
  "evidence_package": {},
  "answer_quality": {}
}
```

현재 구현 특성:

- workflow가 실패 상태로 끝나면 `AgentClient`가 `error` 내부 event를 만들고, `ChatService`가 SSE `error` payload로 변환한다.
- `status`, `stage`, `error_stage`, `error_message`, `error_code`, `retryable`, `output_type`은 optional metadata지만 workflow error에서는 기본값을 채워 보낸다.
- `stage`는 기존 호환 alias이며, 새 클라이언트는 `error_stage`를 우선 사용할 수 있다.
- workflow 내부 진단은 `workflow_error.diagnostic_message`와 `workflow_error.details`에만 남긴다. SSE에는 `public_error`와 안전한 `message`/`error_message`만 노출하며, Pydantic schema명, 누락 field명, stack trace, file path 같은 내부 진단 문자열은 포함하지 않는다.
- analysis code validation은 내부 안전 gate다. 내부 `workflow_error.stage` 또는 `workflow_error.details.internal_stage`가 `code_validation`일 수 있지만, public SSE의 `stage`, `error_stage`, `error_code`, `message`, `public_error`는 `analysis_repair_failed`로 정규화한다.
- `evidence_package`, `answer_quality`가 workflow final state 또는 `output`에 있으면 `error` payload에도 보존된다.
- 존재하지 않는 `source_id`를 새 채팅에서 요청한 경우 `session_id` 없이 `error_code="invalid_source_id"`를 반환할 수 있다.
- router 단계 예외처럼 workflow 밖에서 발생한 오류는 `message` 중심의 단순 `error` payload로 떨어질 수 있으므로, 프론트엔드는 `message`를 계속 기본 표시값으로 사용한다.

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

- 정상 실행과 기존 세션 재개에서는 `session` 이벤트가 먼저 와서 `session_id`, `run_id`를 세팅한다
- `approval_required.pending_approval`은 parse 가능한 객체다
- `done.answer` 또는 누적 `chunk`로 최종 답을 복원할 수 있다
- `error.message`는 사용자에게 보여줄 수 있는 문자열이다
- `done.status`가 `failed`/`cancelled`이면 최종 응답을 실패/취소 상태로 표시할 수 있다
- `done.evidence_package`, `done.answer_quality`, `error.evidence_package`, `error.answer_quality`는 없을 수 있는 optional metadata다

따라서 SSE 이름이나 핵심 필드명(`session_id`, `run_id`, `pending_approval`, `delta`, `answer`, `message`)을 바꾸면 프론트엔드와 문서를 함께 수정해야 한다.

## 검토 체크리스트

- [ ] 새 SSE event를 추가했다면 프론트엔드 parser를 함께 수정했는가
- [ ] 오류 payload에 새 필드를 추가했다면 backward compatibility를 확인했는가
- [ ] `approval_required` shape 변경 시 `pending-approval` GET 응답도 같은 shape를 유지하는가
- [ ] `evidence_package`/`answer_quality`를 추가했다면 `output` 내부 값과 top-level 값이 같은 의미를 유지하는가
- [ ] workflow error와 router-level exception의 payload 차이를 프론트엔드가 모두 처리하는가

## 발표용 framing

현재 시스템의 장점은 SSE로 **session → thought → approval/done** 흐름이 명확하다는 점이다.
오류 계약은 기존 `message` 호환성을 유지하면서 `stage`, `error_code`, `retryable`, evidence metadata를 optional로 추가한 상태다. 발표에서는 기존 이벤트 이름과 core field는 유지하고, 실패 원인과 근거 부족 상태를 additive metadata로 노출한다고 설명하는 것이 정확하다.
