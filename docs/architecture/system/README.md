# 시스템

이 디렉터리는 시스템 전체의 구조/API 진입점을 설명하는 문서를 모아둔다.
질문의 시간 순서와 workflow state 계약은 각각 [질문 흐름](../request-lifecycle.md), [공유 상태](../shared-state.md)를 기준으로 보고, 여기서는 backend/frontend 구조와 public API 계약을 중심으로 다룬다.

## 포함 문서

| 문서 | 설명 | 기준 구현 |
|---|---|---|
| [백엔드 구조](./backend-structure.md) | backend module/orchestration 구조와 책임 경계 | `backend/app/` |
| [프론트엔드 구조](./frontend-structure.md) | Workbench entrypoint, hook, API client 구조 | `frontend/src/app/`, `frontend/src/lib/api.ts` |
| [API 개요 및 명세](./api-spec.md) | FastAPI public route/method/path 계약 | `backend/app/main.py`, `backend/app/modules/` |
| [API / SSE 오류 계약](./api-sse-error-contract.md) | 채팅 SSE 이벤트 순서, payload, 오류 처리 계약 | `backend/app/modules/chat/router.py`, `backend/app/orchestration/client.py`, `frontend/src/app/hooks/useAnalysisPipeline.ts` |

## 읽는 순서

1. 전체 요청 흐름은 [질문 흐름](../request-lifecycle.md)을 먼저 읽는다.
2. backend module 책임은 [백엔드 구조](./backend-structure.md)를 읽는다.
3. frontend Workbench 진입점과 상태 관리는 [프론트엔드 구조](./frontend-structure.md)를 읽는다.
4. public route와 SSE 계약은 [API 개요 및 명세](./api-spec.md), [API / SSE 오류 계약](./api-sse-error-contract.md)을 함께 확인한다.

## 유지 기준

- public router mount, HTTP method/path, SSE event name이 바뀌면 API 문서를 갱신한다.
- backend module family나 orchestration 책임이 바뀌면 [백엔드 구조](./backend-structure.md)를 갱신한다.
- Workbench entrypoint, SSE/approval handling, API type이 바뀌면 [프론트엔드 구조](./frontend-structure.md)를 갱신한다.
- 검증은 아래 명령을 기준으로 한다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```
