# AI Agent

이 디렉터리는 AI Agent 실행을 추적하고 운영 상태를 이해하는 데 필요한 문서를 모아둔다.
현재는 trace와 logging 구조를 중심으로 설명한다.

## 포함 문서

| 문서 | 설명 | 기준 구현 |
|---|---|---|
| [Trace 및 로깅 구조](./trace-and-logging.md) | `trace_id`, `session_id`, `run_id`, `stage` 기준의 실행 로그와 summary 구조 | `backend/app/orchestration/client.py`, `backend/app/modules/chat/router.py` |

## 읽는 순서

1. AI Agent의 일반 실행 흐름은 [질문 흐름](../architecture/request-lifecycle.md)을 기준으로 본다.
2. 실행 이력, 승인 대기, 오류 추적 방식을 확인할 때 [Trace 및 로깅 구조](./trace-and-logging.md)를 읽는다.
3. state key와 SSE-facing output은 [공유 상태](../architecture/shared-state.md)를 함께 확인한다.

## 유지 기준

- trace/logging identifier나 저장 위치가 바뀌면 [Trace 및 로깅 구조](./trace-and-logging.md)를 갱신한다.
- workflow node/edge 변경은 이 디렉터리보다 [질문 흐름](../architecture/request-lifecycle.md)과 [workflow wrapper 문서](../architecture/orchestration/workflows.md)를 우선 갱신한다.
- 검증은 architecture docs harness를 기준으로 한다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```
