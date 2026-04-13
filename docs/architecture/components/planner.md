# Planner 컴포넌트

> 현재 브랜치 기준으로는 메인 워크플로우 안에 독립된 `planner` 노드가 없다. 이 문서는 기존 문서 집합과 용어를 이해하기 위한 참고 문서이며, 실제 런타임 분기 구조는 `intake_flow`와 각 서브그래프가 나눠 담당한다.

## 책임

planner 개념은 문서상으로는 dataset-selected 질문을 세밀하게 분기하는 coordinating component를 뜻한다. 하지만 현재 브랜치의 실제 구현은 이 책임이 하나의 planner 서비스에 모여 있지 않고, `intake_flow`, `preprocess_flow`, `analysis_flow`, `rag_flow`, `guideline_flow`로 분산되어 있다.

## 관련 노트

- [[architecture/README|아키텍처 문서 안내]]
- [[architecture/request-lifecycle|질문 흐름]]
- [[architecture/shared-state|공유 상태]]
- [[architecture/components/main-workflow|메인 워크플로우 컴포넌트]]
- [[architecture/components/guideline|Guideline 컴포넌트]]
- [[architecture/components/analysis|Analysis 컴포넌트]]

## 메인 그래프에서의 위치

- 현재 브랜치에는 독립된 `planner` node가 없다.
- 가장 가까운 대응 관계는 아래와 같다.
  - 최상위 coarse intent 결정: `backend/app/orchestration/intake_router.py`
  - 전처리 필요성 판단: `backend/app/orchestration/workflows/preprocess.py`
  - 분석 질문 구조화: `backend/app/orchestration/workflows/analysis.py`

## 관련 구현 위치

- `backend/app/orchestration/intake_router.py`
- `backend/app/orchestration/ai.py`
- `backend/app/orchestration/workflows/analysis.py`
- `backend/app/orchestration/builder.py`

## 현재 브랜치에서 planner 역할이 분산된 위치

### 1. intake의 coarse routing

- 구현 위치
  - `backend/app/orchestration/intake_router.py`
  - `backend/app/orchestration/ai.py`
- 역할
  - no-dataset vs dataset-selected 구분
  - `general_question` / `clarification` / `data_pipeline` 분기
  - `handoff.ask_*` 플래그 생성

### 2. preprocess의 실행 전 판단

- 구현 위치
  - `backend/app/orchestration/workflows/preprocess.py`
- 역할
  - 실제 전처리 필요 여부 판단
  - 승인/수정/취소 분기

### 3. analysis의 질문 구조화

- 구현 위치
  - `backend/app/orchestration/workflows/analysis.py`
  - `backend/app/modules/analysis/run_service.py`
- 역할
  - `QuestionUnderstanding`
  - `ColumnGroundingResult`
  - `AnalysisPlanDraft`
  - 최종 `AnalysisPlan`
  - clarification 회수

## 문서상 planner와 실제 런타임의 차이

- 문서상 planner는 `dataset_lookup`, `retrieval_qa`, `analysis`를 정밀 분기하는 단일 컴포넌트다.
- 실제 런타임은 `dataset_lookup_terminal`이 없고, selected-dataset 요청이 모두 `preprocess_flow`를 먼저 지난다.
- 현재 브랜치에서 가장 planner에 가까운 계약은 `planning_result`가 아니라 `handoff`다.

## 이 문서를 읽는 방법

- 현재 코드 기준 설명이 필요하면 `request-lifecycle.md`, `components/main-workflow.md`, `ai-agent/backend-accuracy-audit.md`를 우선 본다.
- 이 파일은 "원래 planner가 하려던 역할이 지금 어디로 분산되어 있는가"를 이해하기 위한 보조 문서다.
