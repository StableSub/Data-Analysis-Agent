# 아키텍처 문서 안내

이 디렉터리는 현재 런타임 구조를 코드 기준으로 따라가기 쉽게 정리한 문서 진입점이다. 목표는 사용자가 질문을 넣었을 때 어떤 경로로 실행이 진행되고, 어떤 상태가 오가며, 각 컴포넌트가 어떤 책임을 가지는지 빠르게 파악할 수 있게 만드는 것이다.

이 디렉터리의 문서는 현재 데이터 분석 AI Agent 런타임을 기준으로 한다. 제품 요구사항과 개선 우선순위는 [제품 요구사항](../product/prd.md), [현재 구현 기준선](../product/current-state-baseline.md), [구현 로드맵](../product/roadmap.md)을 먼저 본다.

## 원천 문서

| 문서 | 소유하는 내용 | 주요 기준 코드 |
|---|---|---|
| `request-lifecycle.md` | 사용자 질문의 runtime flow, node/edge/terminal 분기 | `backend/app/orchestration/builder.py`, `backend/app/orchestration/intake_router.py` |
| `shared-state.md` | workflow state key, approval/output payload, shared context | `backend/app/orchestration/state.py`, `backend/app/orchestration/client.py` |
| `components/*.md` | 각 subgraph 내부 node와 core term | `backend/app/orchestration/workflows/*.py` |
| `system/api-spec.md` | public FastAPI route/method/path 계약 | `backend/app/main.py`, mounted routers |
| `system/backend-structure.md` | backend module/orchestration 구조 | `backend/app/` |
| `system/frontend-structure.md` | Workbench entrypoint, hook, API client 구조 | `frontend/src/app/`, `frontend/src/lib/api.ts` |

부모 문서는 상세 내용을 반복하지 않고 소유 문서로 연결한다. 코드 변경이 위 기준 파일을 움직이면 같은 변경에서 해당 소유 문서를 검토한다.

## 관련 노트

- [[AGENTS|프로젝트 지식 베이스]]
- [[architecture/AGENTS|아키텍처 문서 가이드]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]

## 읽는 순서

1. [질문 흐름](./request-lifecycle.md)
2. [공유 상태](./shared-state.md)
3. 시스템 문서
   - [API 개요 및 명세](./system/api-spec.md)
   - [백엔드 구조](./system/backend-structure.md)
   - [프론트엔드 구조](./system/frontend-structure.md)
4. 컴포넌트 문서
   - [메인 워크플로우](./components/main-workflow.md)
   - [Guideline](./components/guideline.md)
   - [Preprocess](./components/preprocess.md)
   - [Analysis](./components/analysis.md)
   - [RAG](./components/rag.md)
   - [Visualization](./components/visualization.md)
   - [Report](./components/report.md)

## 각 문서가 답하는 질문

- `request-lifecycle.md`
  - 사용자 질문이 들어오면 어떤 순서로 노드가 실행되는가?
  - 어떤 조건에서 preprocess, analysis, rag, visualization, report로 분기되는가?
  - clarification, fail, cancelled, success는 어디서 결정되는가?
- `shared-state.md`
  - 어떤 state 필드가 전체 흐름에서 공유되는가?
  - 각 필드는 어디서 생성되고 어디서 소비되는가?
- `components/`
  - 각 컴포넌트 내부 노드는 어떤 input/output/logic을 가지는가?
  - 컴포넌트 내부에서 approval, clarification, fail은 어떻게 처리되는가?
  - 현재 단계에서는 `main-workflow`, `guideline`, `preprocess`, `analysis`, `rag`, `visualization`, `report` 문서가 채워진다.
  - 별도 planner node는 없으며, planner 용어는 `request-lifecycle.md`의 용어 정리를 따른다.

## 기준 구현 위치

- 메인 워크플로우 조립
  - `backend/app/orchestration/builder.py`
- 공유 상태 계약
  - `backend/app/orchestration/state.py`
- workflow 실행 스트리밍과 approval 이벤트 처리
  - `backend/app/orchestration/client.py`
- intake 분기와 coarse intent 판단
  - `backend/app/orchestration/intake_router.py`
- 최종 일반/데이터 응답 생성
  - `backend/app/orchestration/ai.py`
