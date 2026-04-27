# API / SSE 오류 계약

## 문서 목적

이 문서는 현재 FastAPI public API와 채팅 SSE 스트림에서 관찰되는 오류 계약을 팀 관점에서 빠르게 확인할 수 있도록 정리한다.
상세 route 목록은 `api-spec.md`를 기준으로 보고, 여기서는 상태 코드·오류 payload·SSE error 이벤트의 운영 의미를 집중해서 정리한다.

## 기준 구현 위치

- `backend/app/modules/chat/router.py`
- `backend/app/modules/chat/service.py`
- `backend/app/modules/chat/schemas.py`
- `backend/app/orchestration/client.py`
- `frontend/src/lib/api.ts`

## 이 문서가 답하는 질문

- HTTP API는 오류를 어떤 형태로 돌려주는가?
- SSE stream은 실패를 어떻게 알리는가?
- approval/resume 흐름에서 404와 SSE error를 어떻게 구분해야 하는가?
- 프론트엔드와 발표 설명에서 무엇을 사실로 말할 수 있는가?

## 공통 HTTP 오류 계약

현재 일반 JSON API는 FastAPI `HTTPException` 기본 형태를 사용한다.
실패 시 프론트엔드는 `frontend/src/lib/api.ts`의 `apiRequest()`에서 응답 JSON의 `detail` 값을 읽어 `ApiError(status, message)`로 변환한다.

정리하면 현재 계약은 다음과 같다.

- 성공
  - `2xx` + JSON body 또는 `204 No Content`
- 실패
  - `4xx/5xx` + JSON body의 `detail` 필드
- 프론트엔드 소비 방식
  - `res.ok === false`이면 `detail` 또는 `statusText`를 메시지로 사용

## SSE 계약 개요

`POST /chats/stream`, `POST /chats/{session_id}/runs/{run_id}/resume`는 `text/event-stream` 응답을 반환한다.
현재 router는 event 이름과 payload를 직접 문자열로 포맷한다.

헤더:

- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`

주요 이벤트 이름:

- `session`
- `thought`
- `chunk`
- `approval_required`
- `done`
- `error`

## SSE 이벤트별 계약

### `session`

초기 세션/실행 식별자 전달용 이벤트다.

주요 필드:
- `session_id`
- `run_id`

### `thought`

중간 진행 상태를 나타낸다.

주요 필드:
- `phase`
- `message`
- `status`

### `chunk`

최종 답변 텍스트를 부분 전송한다.

주요 필드:
- `delta`

### `approval_required`

실행이 사용자 승인 단계에서 멈췄음을 뜻한다.
오류가 아니라 **정상적인 중단 상태**다.

주요 필드:
- `session_id`
- `run_id`
- `pending_approval`
- `thought_steps`

### `done`

정상 종료 이벤트다.

주요 필드:
- `answer`
- `session_id`
- `run_id`
- `thought_steps`
- 선택 필드: `preprocess_result`, `visualization_result`, `output_type`, `output`

### `error`

세부 규칙:
- 내부 `done` 이벤트에 `answer`가 없으면 누적한 `chunk`를 합쳐 최종 답변으로 사용한다.
- 최종 답변이 비어 있으면 `응답을 생성하지 못했습니다.`를 기본값으로 쓴다.
- `append_assistant_message=True`일 때만 저장소 history에 assistant 메시지를 추가한다.

프론트엔드 동작:
- `done`을 받으면 `state="success"`로 바꾼다.
- `preprocess_result.status == "applied"`이고 `output_source_id`가 있으면 업로드 데이터셋 목록에 전처리 결과 source를 추가한다.
- `visualization_result`가 있으면 최신 시각화 결과로 저장한다.

### 6. `error`

생성 위치:
- `backend/app/modules/chat/router.py`의 `event_generator()` 예외 처리

payload:

```json
{
  "message": "..."
}
```

오류가 만들어지는 방식:
- `chat_service.ask_stream(...)` 또는 `chat_service.resume_run_stream(...)`에서 예외가 발생하면 router가 `error` 이벤트를 한 번 더 감싸서 내려준다.
- 프론트엔드는 `message`를 읽어 `Error(...)`를 던지고 `state="error"`로 전환한다.

## pending approval 조회 계약

`GET /chats/{session_id}/runs/{run_id}/pending-approval`는 JSON 응답이며 SSE가 아니다.

- 성공 시 `backend/app/modules/chat/schemas.py::PendingApprovalResponse` 형태를 반환한다.
- `chat_service.get_pending_approval(...)`가 `None`이면 `404 pending approval not found`를 반환한다.
- 프론트엔드의 `frontend/src/lib/api.ts::fetchPendingApproval(...)`는 이 응답을 일반 JSON API로 다룬다.

## resume 요청 계약

`POST /chats/{session_id}/runs/{run_id}/resume` 요청 body는 `backend/app/modules/chat/schemas.py::ResumeRunRequest` 기준이다.

필드:
- `decision`: `approve` | `revise` | `cancel`
- `stage`: `preprocess` | `visualization` | `report`
- `instruction`: 선택 문자열

서버는 `instruction`이 없으면 빈 문자열로 agent resume payload에 넣는다.

## 프론트엔드 파서 가정

`frontend/src/app/hooks/useAnalysisPipeline.ts`의 SSE 파서는 아래 가정에 의존한다.

- 각 이벤트는 빈 줄(`\n\n`)로 구분된다.
- 이벤트 이름은 `event:` 줄에서 읽는다.
- payload는 JSON 객체여야 하며, 이벤트별 키가 빠지면 즉시 예외로 이어질 수 있다.
- `session` → `thought/chunk` → `approval_required` 또는 `done` 순서가 기본 happy path다.

## 운영상 주의점

- 새 SSE 이벤트를 추가하면 `frontend/src/app/hooks/useAnalysisPipeline.ts`와 `docs/architecture/system/api-spec.md`를 함께 갱신해야 한다.
- `pending_approval` shape가 바뀌면 `backend/app/modules/chat/schemas.py`와 `frontend/src/lib/api.ts` 타입을 같이 바꿔야 한다.
- 단순 HTTP 오류와 SSE stream 내부 `error` 이벤트는 소비 방식이 다르므로 같은 것으로 문서화하면 안 된다.

## 발표용 요약

발표에서는 아래 한 문장으로 설명하는 것이 안전하다.

> 현재 채팅 실행은 `session → thought/chunk → approval_required 또는 done → 필요 시 error` 형태의 SSE 계약으로 동작하며, 승인 대기와 재개는 별도 JSON API와 resume stream으로 이어진다.
