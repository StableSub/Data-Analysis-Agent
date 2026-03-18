# docs-코드 정합성 재검증 리포트

## 1. 목적

- 이 문서는 `docs/*.md`와 현재 `backend/app` 구조가 실제로 정합한지 다시 확인한 결과다.
- 이번 판정은 구조/흐름/API/상태 계약 기준이다.

## 2. 검증 기준 문서

- [backend-architecture-guidelines.md](/Users/anjeongseob/Desktop/Project/capstone-project/docs/backend-architecture-guidelines.md)
- [backend-feature-design.md](/Users/anjeongseob/Desktop/Project/capstone-project/docs/backend-feature-design.md)
- [backend-data-flow-design.md](/Users/anjeongseob/Desktop/Project/capstone-project/docs/backend-data-flow-design.md)
- [backend-state-session-design.md](/Users/anjeongseob/Desktop/Project/capstone-project/docs/backend-state-session-design.md)
- [api-specification.md](/Users/anjeongseob/Desktop/Project/capstone-project/docs/api-specification.md)

허용된 현행 제약

- direct `/report`, `/rag/query`의 `context` semantics 미반영
- `SessionSource.session_id` 타입 불일치
- `InMemorySaver` 기반 비영속 run/approval state
- `__pycache__`와 빈 디렉터리 잔재

## 3. 수행한 검증

정적 검증

- `rg -n "backend\.app\.(api|domain|ai|rag|data_eng)|from \.{1,3}(api|domain|ai|rag|data_eng)" backend/app backend/tests`
  - 결과: active code/test 기준 legacy top-level 경로 역참조 없음
- `find backend/app/application backend/app/ports backend/app/ai backend/app/api backend/app/data_eng backend/app/domain backend/app/rag -type f -name '*.py'`
  - 결과: source `.py` 없음

런타임 검증

- `python3 -m unittest backend.tests.test_use_cases backend.tests.test_api_routes`
  - 결과: `8 tests`, `OK`
- `python3 -m py_compile $(find backend/app -name '*.py' -type f | tr '\n' ' ')`
  - 결과: 통과
- `from backend.app.main import app`
  - 결과: 필수 route 누락 없음

## 4. 전체 판정

**전체 verdict: aligned**

- 현재 실구현 소유자는 `core`, `modules`, `orchestration`만 가진다.
- router/service/repository/orchestration 경계가 docs 기준과 맞다.
- public API path, 핵심 response shape, SSE 이벤트 이름이 유지된다.
- 상태/세션 계약도 docs와 충돌하지 않는다.

## 5. 문서별 판정

| 문서 | 판정 | 근거 |
|---|---|---|
| `backend-architecture-guidelines.md` | aligned | 실구현 소유자가 `core/modules/orchestration`만 남음 |
| `backend-feature-design.md` | aligned | 각 모듈의 현재 책임과 비책임이 코드와 일치 |
| `backend-data-flow-design.md` | aligned | upload/delete/chat/preprocess/viz/report/export/rag 흐름이 코드와 일치 |
| `backend-state-session-design.md` | aligned | `session_id/run_id/thread_id/pending_approval` 계약이 유지됨 |
| `api-specification.md` | aligned | 실제 등록 route와 핵심 schema/SSE 계약이 유지됨 |

## 6. 남아 있는 비구조 이슈

아래는 이번 구조 정합성 검증에서 허용된 현행 제약이다.

- direct `/report`, `/rag/query`의 `context` semantics 미반영
- `SessionSource.session_id` 타입 불일치
- `InMemorySaver` 기반 비영속 run/approval state

이 셋은 구조 정합성 위반이 아니라, 별도 behavior/schema 개선 과제로 분리한다.

## 7. 최종 결론

현재 백엔드는 docs가 기대한 최종 상태에 도달했다.

> `core + modules + orchestration`가 실제 소유권을 가지며,  
> legacy top-level 기술 축은 source 기준으로 제거되었고,  
> public contract와 state/session contract도 유지된다.
