# 백엔드 상태 / 세션 설계서

## 1. 목적

- 이 문서는 현재 백엔드의 `session`, `run`, `workflow state`, `approval state` 계약을 정의한다.
- 기준은 현재 코드 구현이며, 구조 리팩토링 중에도 이 계약은 유지해야 한다.

## 2. 핵심 식별자

- `dataset_id`
  - `datasets.id`
- `source_id`
  - dataset 외부 식별자
  - preprocess / rag / visualization / chat dataset 선택 공통 키
- `session_id`
  - `chat_sessions.id`
- `run_id`
  - 질문 1회 실행 단위 식별자
- `report_id`
  - `reports.id`
- `result_id`
  - `analysis_results` export 대상

## 3. 상태 계층

현재 시스템의 상태는 4계층으로 나뉜다.

1. durable session state
   - `chat_sessions`
   - `chat_messages`
2. durable data/result state
   - `datasets`
   - `reports`
   - `rag_sources`
   - `rag_chunks`
   - `analysis_results`
3. workflow runtime state
   - LangGraph snapshot
4. approval state
   - `pending_approval`
   - `revision_request`
   - `approved_plan`

즉, session과 workflow state는 같은 개념이 아니다.

## 4. session

구현 위치

- [modules/chat/session_service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/session_service.py)
- [modules/chat/repository.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/repository.py)

정의

- `session_id`는 durable chat container다.
- session은 아래를 포함한다.
  - session 메타데이터
  - 사용자/assistant 메시지 로그

현재 정책

- `session_id`가 없으면 새 session을 만든다.
- `session_id`가 잘못됐어도 현재는 새 session을 만든다.

## 5. run

구현 위치

- [modules/chat/run_service.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/modules/chat/run_service.py)

정의

- `run_id`는 agent 실행 단위다.
- 같은 session 안에서도 질문마다 새 `run_id`가 생길 수 있다.
- 현재 `uuid.uuid4().hex`로 생성한다.

## 6. workflow state

구현 위치

- [orchestration/state.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/state.py)
- [orchestration/client.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py)

정의

- workflow state는 LangGraph가 유지하는 실행 중 딕셔너리다.
- DB가 아니라 checkpointer에 저장된다.

현재 영속성

- checkpointer는 `InMemorySaver`
- 따라서 workflow state는 비영속이다.

## 7. approval state

구현 위치

- [orchestration/workflows/preprocess.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/preprocess.py)
- [orchestration/workflows/visualization.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/visualization.py)
- [orchestration/workflows/report.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/workflows/report.py)

정의

- approval state는 `interrupt(payload)`로 생성되는 승인 대기 상태다.
- 핵심 키는 아래와 같다.
  - `pending_approval`
  - `revision_request`
  - `approved_plan`

현재 영속성

- approval state 역시 `InMemorySaver`에만 있다.
- 서버 재시작 시 유지되지 않는다.

## 8. thread_id 규칙

구현 위치

- [orchestration/client.py](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py)

현재 규칙

- `thread_id = run_id or session_id or "default"`

의미

- chat 흐름에서는 보통 `run_id`가 state 격리 단위가 된다.
- direct `/report`, `/rag/query`처럼 `run_id`, `session_id`를 넘기지 않는 흐름은 `"default"` thread를 공유할 수 있다.

## 9. direct API와 session 관계

채팅 세션 계약을 직접 쓰는 경로

- `POST /chats/`
- `POST /chats/stream`
- `POST /chats/{session_id}/runs/{run_id}/resume`
- `GET /chats/{session_id}/runs/{run_id}/pending-approval`
- `GET /chats/{session_id}/history`
- `DELETE /chats/{session_id}`

채팅 세션 계약을 직접 쓰지 않는 경로

- datasets API
- direct preprocess API
- direct visualization API
- export API

중간 성격 경로

- direct `/report`
- direct `/rag/query`

이 둘은 chat session-bound는 아니지만, 내부적으로는 shared [AgentClient](/Users/anjeongseob/Desktop/Project/capstone-project/backend/app/orchestration/client.py)를 사용한다.

## 10. 의도적으로 유지한 현행 제약

- direct `/report`, `/rag/query`에서 넘긴 `context`는 현재 의미 있게 반영되지 않는다.
- `SessionSource`는 주 흐름에 연결되지 않은 inactive 구조다.
- durable run state는 아직 없다.

## 11. 유지해야 할 계약

- `session_id`가 없거나 잘못되면 새 session을 만든다.
- chat 실행 시 `run_id`를 생성한다.
- `session` SSE 이벤트를 먼저 보낸다.
- approval 단계에서는 `pending_approval`, `revision_request`, `approved_plan` 키를 그대로 유지한다.
- `thread_id = run_id or session_id or "default"` 규칙을 유지한다.
