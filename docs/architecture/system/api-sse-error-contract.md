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

router 수준 예외를 SSE 프레임으로 감싼 이벤트다.
현재 payload는 단순하다.

주요 필드:
- `message`

중요한 점:
- 현재 `error` 이벤트는 구조화된 에러 코드가 없다.
- HTTP status를 이미 보낸 뒤 스트림 내부에서 예외가 발생하면, 클라이언트는 status code 대신 SSE `error` 이벤트를 받는다.
- 따라서 발표에서는 "스트림 실패 시 세분화된 에러 taxonomy가 완비돼 있다"고 말하면 안 된다.

## approval / resume 관련 오류 구분

### 1. `GET /chats/{session_id}/runs/{run_id}/pending-approval`

- 승인 대기 상태가 없으면 `404`
- detail: `pending approval not found`

이 경우는 "실행 실패"가 아니라 "현재 재개할 승인 상태가 없음"에 가깝다.

### 2. `POST /chats/{session_id}/runs/{run_id}/resume`

- 세션이 없으면 스트림 내부에서 예외가 발생해 SSE `error` 이벤트로 전달될 수 있다.
- router에서 별도 `HTTPException`으로 세분화하지 않는다.

즉 현재 resume 경로는 일부 오류가 HTTP status가 아니라 SSE `error.message`로만 노출될 수 있다.

## 주요 REST API 오류 패턴 요약

| 영역 | 대표 상태 코드 | 의미 |
|---|---:|---|
| `datasets` | `400`, `404`, `500` | 파일명 누락, 데이터셋 없음, 업로드 실패 |
| `eda` | `400`, `404`, `422` | 잘못된 분포 요청, 데이터 없음, 지원 불가 요청 |
| `analysis` | `400`, `404`, `500` | 잘못된 실행 입력, 소스 없음, 내부 실행 실패 |
| `preprocess` | `400`, `404` | 잘못된 연산 또는 소스 없음 |
| `vizualization` | `400`, `404`, `422`, `500` | 잘못된 컬럼, 데이터 없음, 내부 실패 |
| `rag` | `204`, `404`, `500` | 결과 없음, 인덱스 없음, 임베딩/검색 실패 |
| `guidelines` | `400`, `404`, `500` | PDF 검증 실패, 대상 없음, 업로드/임베딩 실패 |
| `report` | `404`, `500` | 세션/리포트 없음, 생성 실패 |
| `export` | `404` | 결과 없음 |
| `chats` 일반 조회/삭제 | `404` | 세션 또는 pending approval 없음 |

## 프론트엔드 해석 계약

`frontend/src/lib/api.ts` 기준으로 현재 프론트엔드의 해석 규칙은 다음과 같다.

- JSON API 실패는 `ApiError.status`, `ApiError.message`로 소비한다.
- `204`는 `undefined` 응답으로 처리한다.
- SSE는 HTTP JSON 오류 래퍼가 아니라 event name 기반으로 처리한다.
- 따라서 동일한 "실패"라도 일반 API와 스트림 API의 클라이언트 처리 방식이 다르다.

## 팀 운영 가이드

### 문서/발표에서 안전하게 말할 수 있는 표현

- "채팅 실행과 재개는 SSE 스트림으로 상태를 전달한다."
- "승인 대기는 별도 `approval_required` 이벤트와 pending approval 조회 API로 관리한다."
- "일반 REST API 오류는 HTTP status와 `detail` 메시지로 전달한다."
- "스트림 내부 예외는 현재 `error` 이벤트의 메시지 중심으로 노출된다."

### 과장하면 안 되는 표현

- "모든 오류가 표준화된 코드 체계로 완전히 분류돼 있다"
- "resume 경로는 모든 실패를 일관된 HTTP 상태 코드로 돌려준다"
- "SSE 오류 payload가 typed contract로 완전히 고정돼 있다"

## 갱신 기준

- `chat/router.py`의 event 이름 또는 payload shape 변경
- `chat/service.py`의 `done`, `approval_required` packaging 변경
- `frontend/src/lib/api.ts`의 `ApiError` 처리 변경
- public router의 status code 정책 변경

## 빠른 점검 체크리스트

- [ ] 새 SSE event 이름을 추가/변경했으면 `api-spec.md`와 이 문서를 함께 수정했다.
- [ ] `detail` 대신 다른 오류 필드를 쓰기 시작했다면 프론트엔드 소비 경로를 함께 수정했다.
- [ ] approval/resume 흐름 변경 시 404와 SSE `error` 경계가 여전히 설명 가능하다.
- [ ] 발표 자료에서 오류 처리 설명이 현재 구현을 넘어서지 않는다.
