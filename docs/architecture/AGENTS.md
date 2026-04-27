# ARCHITECTURE DOCS 지식 베이스

## 개요
코드를 따라가는 architecture 문서다. 이 파일들은 현재 runtime 동작을 설명하며, 최종 기준은 코드다.

## 관련 노트
- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[AGENTS|프로젝트 지식 베이스]]

## 확인 위치
| 작업 | 위치 | 참고 |
|---|---|---|
| End-to-end request flow | `request-lifecycle.md` | orchestration 분기를 반영한다 |
| 공유 workflow state | `shared-state.md` | `backend/app/orchestration/state.py`를 반영한다 |
| 메인 workflow component 문서 | `components/main-workflow.md` | builder/client 교차 참조 |
| 기능 문서 | `components/*.md` | guideline/preprocess/analysis/rag/visualization/report |

## 규칙
- 이 문서들은 runtime code의 설명용 동반 문서다. orchestration/state 계약이 움직이면 함께 갱신한다.
- 파일 참조는 모호한 개념 설명보다 구체적인 경로(`backend/app/...`)로 쓴다.
- 현재 node name, route name, payload key, terminal output type을 정확히 반영한다.

## 갱신 기준
- workflow node/edge/terminal 변경은 `request-lifecycle.md`와 `components/main-workflow.md`에 반영한다.
- state key, payload shape, approval/output contract 변경은 `shared-state.md`에 반영한다.
- public route, backend/frontend entrypoint, 검증 명령 변경은 `system/*.md` 또는 `docs/development/*.md`의 소유 문서에 반영한다.

## 금지 패턴
- workflow/state 변경 뒤 문서가 drift되도록 두지 않는다.
- 계획 중인 architecture를 현재 runtime 동작처럼 설명하지 않는다.
- route-name 또는 payload-key 차이를 “정리된” 용어 뒤에 숨기지 않는다. 실제 이름을 문서화한다.

## 고유 스타일
- `request-lifecycle.md`와 `shared-state.md`가 문서 진입점이다.
- `components/`는 frontend UI component가 아니라 runtime component family를 반영한다.

## 참고
- `backend/tests/test_architecture_docs.py`가 이 영역 일부를 검증한다. 이 문서들은 테스트에 민감하다.
- `builder.py`, `state.py`, `client.py` 또는 주요 subgraph가 바뀌면 같은 변경에서 이 디렉터리를 검토한다.
