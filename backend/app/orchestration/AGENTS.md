# ORCHESTRATION 지식 베이스

## 개요
기능 간 workflow 계층이다. LangGraph 조립, 라우팅, 공유 상태, 최종 답변 구성, SSE-facing 출력 계약을 담당한다.

## 관련 노트
- [[AGENTS|프로젝트 지식 베이스]]
- [[docs/architecture/README|아키텍처 문서 안내]]
- [[docs/architecture/request-lifecycle|질문 흐름]]
- [[docs/architecture/shared-state|공유 상태]]
- [[docs/architecture/backend-workflow|Backend workflow]]

## 확인 위치
| 작업 | 위치 | 참고 |
|---|---|---|
| 메인 그래프 분기 | `builder.py` | terminal 전환과 subgraph 연결의 진입점 |
| 런타임 스트리밍 | `client.py` | SSE chunking, approval interrupt, 최종 payload 형태 |
| 공유 상태 계약 | `state.py` | 모든 subgraph에서 소비하는 TypedDict payload |
| 최종 답변 구성 | `ai.py`, `builder.py` | general/data answer 생성과 merged context 전달 |
| Intake 라우팅 | `intake_router.py` | dataset-selected와 no-dataset 진입 분리 |
| Subgraph wrapper | `workflows/` | workflow별 얇은 wrapper 계층; 일관성을 유지한다 |

## 규칙
- `builder.py`, `client.py`, `state.py`, `ai.py`는 논리적으로 함께 맞춘다. 계약 변경은 한 파일에만 머무는 경우가 드물다.
- `orchestration/`은 모듈 간 라우팅과 상태 handoff를 담당한다. 여러 모듈을 가로지르는 규칙이 아니라면 module-specific business rule을 여기로 옮기지 않는다.
- 기존 state key를 rename하기보다 additive key를 선호한다. 프론트엔드 스트리밍과 문서가 key 안정성에 의존한다.
- `workflows/`는 flat wrapper 계층이다. workflow-specific 동작은 해당 파일에 두고, workflow 간 공유 helper는 상위 파일에 둔다.

## 갱신 기준
- `builder.py`의 node, edge, terminal output type이 바뀌면 `docs/architecture/request-lifecycle.md`와 `docs/architecture/backend-workflow.md`와 `docs/architecture/orchestration/workflows.md`를 같은 변경에서 갱신한다.
- `state.py`의 key나 approval/output payload가 바뀌면 `docs/architecture/shared-state.md`, `client.py`, 프론트엔드 pipeline 계약을 함께 확인한다.
- SSE event shape, resume payload, final output packaging이 바뀌면 `docs/system/api-spec.md`와 `frontend/src/app/hooks/useAnalysisPipeline.ts`를 함께 확인한다.

## 금지 패턴
- 모든 consumer를 갱신하지 않고 `planning_result`, `handoff`, `output`, approval payload key, final result key를 함부로 rename하지 않는다.
- module service가 이미 담당하는 로직을 orchestration에 중복 구현하지 않는다.
- `frontend/src/app/hooks/useAnalysisPipeline.ts`를 확인하지 않고 thought-step 문구나 최종 payload 형태를 바꾸지 않는다.
- `docs/architecture/request-lifecycle.md`와 `shared-state.md`를 갱신하지 않고 workflow 라우팅을 바꾸지 않는다.

## 고유 스타일
- 중앙 “agent api” 계층은 없다. `modules/chat`이 `AgentClient`를 통해 workflow로 진입한다.
- 최종 답변 packaging은 개별 모듈이 아니라 이 계층(`ai.py`, `builder.py`)에서 처리한다.
- Approval interrupt는 first-class runtime event다. 취소/수정 경로도 happy path만큼 중요하다.

## 참고
- 가장 큰 hotspot은 `builder.py`, `client.py`, `state.py`, `ai.py`다.
- 변경이 streaming, approval, answer context에 영향을 주면 수정 전에 관련 hotspot을 모두 읽는다.
