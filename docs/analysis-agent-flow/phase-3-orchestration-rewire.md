# Phase 3. Orchestration Rewire

## Summary

이 phase의 목표는 `dataset_qa -> rag` 기본 경로를 줄이고, dataset selected path를 `planner -> preprocess(optional) -> analysis` 중심으로 재배선하는 것이다.

이 phase는 planning 전 evidence provider를 `guideline_context`로 고정하는 단계이기도 하다.

## Current State

현재 main workflow는 아래 특성을 가진다.

- dataset selected path가 `dataset_qa`와 `data_pipeline`로 갈라진다.
- `dataset_qa`는 기본적으로 `rag_flow`로 들어간다.
- `data_pipeline`은 `preprocess_flow` 이후 `analysis_flow` 또는 `rag_flow`로 이어진다.
- `guideline_flow`는 `analysis_flow` 또는 `rag_flow` 뒤에 붙는다.
- 최종 응답은 `merged_context` 기반 `data_qa_terminal`에서 생성된다.

현재 확인 기준 코드는 아래다.

- `backend/app/orchestration/intake_router.py`
- `backend/app/orchestration/builder.py`
- `backend/app/orchestration/workflows/guideline.py`
- `backend/app/orchestration/workflows/rag.py`

## Decisions Locked In This Phase

### 새 기본 경로

dataset selected 질문의 새 기본 경로는 아래 순서로 고정한다.

1. dataset selected
2. `dataset_context`
3. `guideline_context`
4. `planner`
5. `preprocess` optional
6. `analysis` as default path
7. optional downstream outputs
   - `visualization`
   - `report`
   - final answer

`fallback_rag`는 위 기본 경로의 예외 route다. planner가 명시적으로 선택한 경우에만 진입한다.

### Evidence provider 정책

- planning 전에 들어가는 evidence는 `guidelines + guideline_rag`가 만든 `guideline_context`다.
- dataset RAG는 planner의 기본 입력이 아니다.
- dataset RAG는 legacy compatibility/fallback retrieval path로만 유지한다.

### Dataset RAG fallback 정책

dataset RAG는 아래 경우에만 허용한다.

- planner가 `route=fallback_rag`를 명시적으로 반환한 경우
- analysis 엔진으로 답하기 어려운 retrieval 성격 질문으로 planner가 판정한 경우
- 파일 형식이나 데이터 상태 때문에 analysis contract를 적용할 수 없다고 planner가 판정한 경우

아래 경우에는 dataset RAG로 보내지 않는다.

- 단순 집계
- 비교
- 추세
- 상관/관계 분석
- 시각화 요청
- 리포트 요청

### Guideline 배선 정책

- `guideline_flow`는 planner 이후 보조 evidence 단계가 아니라 planner 이전 입력 준비 단계로 재배치한다.
- planner는 `guideline_context`를 읽고 `analysis_plan`, `need_report`, `guideline_context_used`를 결정한다.

### General question 경로

- dataset가 선택되지 않은 일반 질문 경로는 유지한다.
- dataset가 선택된 상태에서도 planner가 `route=general_question`을 반환하면 general answer 경로로 보낼 수 있다.
- 단, dataset selected 상태의 기본값은 general이 아니라 analysis 검토다.

## Implementation Changes

### Intake and orchestration

- 기존 intake의 `dataset_qa` / `data_pipeline` 이원 분기를 planner 중심 단일 dataset-selected 경로로 축소한다.
- dataset selected 상태에서는 먼저 `dataset_context`와 `guideline_context`를 만든 뒤 planner를 호출한다.
- preprocess 실행 여부, analysis 진입 여부, fallback RAG 진입 여부, visualization/report/final answer downstream 여부는 planner 결과를 따른다.

### Guideline integration

- `guideline_flow`는 planner 전 입력 준비 역할로 이동한다.
- `guideline_context` contract를 merged context 이전에도 사용 가능하게 만든다.

### RAG integration

- dataset RAG는 default path에서 제거한다.
- dataset RAG 진입은 planner가 명시적으로 fallback route를 반환할 때만 허용한다.
- dataset RAG를 planner 입력 evidence와 혼동하지 않게 변수명과 route 이름을 정리한다.

## Out of Scope

- planner 책임 변경
- visualization detailed chart planning 변경
- reports direct CSV reread 제거
- downstream 표현 계층의 full 정리

## Completion Criteria

- dataset selected 기본 경로가 `planner -> preprocess(optional) -> analysis` 중심으로 재배선된다.
- planner 전 evidence provider가 `guideline_context`인지 dataset RAG인지 더 이상 모호하지 않다.
- dataset RAG는 default path가 아니라 fallback path로만 남는다.
- dataset selected 상태의 정량 질문은 기본적으로 analysis 경로를 탄다.
- `report`와 final answer는 analysis 이후의 optional downstream outputs로 취급되며, overview와 phase 문서 사이에 직렬 오해가 없다.

## Handoff To Next Phase

- `Phase 4`는 이미 analysis 중심으로 정리된 upstream 결과를 받아 visualization/reports를 downstream으로 고정한다.
- `Phase 4`는 dataset file reread 없이도 downstream이 동작하도록 `analysis_result`, `dataset_context`, `guideline_context`를 사용한다.

## Validation Checklist

- 이 문서만 보고 아래 질문에 답할 수 있어야 한다.
- planning 전에 들어가는 evidence는 guideline인가, dataset RAG인가?
- 답: `guideline_context`다.
- dataset RAG는 제거되는가?
- 답: 아니다. fallback path로 남는다.
- 어떤 질문이 기본적으로 fallback RAG로 가는가?
- 답: planner가 analysis 불가 또는 retrieval-only로 판정한 경우만 간다.
- `guideline_flow`는 planner 전인가 후인가?
- 답: planner 전 입력 준비 단계다.
