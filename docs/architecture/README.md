# 아키텍처 문서 안내

이 디렉터리는 현재 런타임 구조를 코드 기준으로 따라가기 쉽게 정리한 문서 진입점이다. 목표는 사용자가 질문을 넣었을 때 어떤 경로로 실행이 진행되고, 어떤 상태가 오가며, 각 컴포넌트가 어떤 책임을 가지는지 빠르게 파악할 수 있게 만드는 것이다.

## 관련 노트

- [[AGENTS|프로젝트 지식 베이스]]
- [[CLAUDE|Claude 작업 가이드]]
- [[architecture/AGENTS|Architecture Docs 가이드]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]

## 읽는 순서

1. [질문 흐름](./request-lifecycle.md)
2. [공유 상태](./shared-state.md)
3. 컴포넌트 문서
   - [메인 워크플로우](./components/main-workflow.md)
   - [Planner](./components/planner.md)
   - [Guideline](./components/guideline.md)
   - [Preprocess](./components/preprocess.md)
   - [Analysis](./components/analysis.md)
   - [RAG](./components/rag.md)
   - [Visualization](./components/visualization.md)
   - [Report](./components/report.md)
4. 현재 브랜치 감사 문서
   - [선택 데이터셋 질문 정확성 감사](./ai-agent/backend-accuracy-audit.md)

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
  - 현재 단계에서는 `main-workflow`, `planner`, `guideline`, `preprocess`, `analysis`, `rag`, `visualization`, `report` 문서가 채워진다.

## System Of Record

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
