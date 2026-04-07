# Phase 2. Planner

## Summary

이 phase의 목표는 현재 분산된 판단 로직을 `planning_result` 단일 계약으로 통합하는 planner를 도입하는 것이다.

이 phase는 planner의 책임 경계를 고정하는 단계다. orchestration 기본 배선의 full rewire는 `Phase 3` 책임이다.

## Current State

현재 판단 로직은 여러 위치에 흩어져 있다.

- intent 분기: `backend/app/orchestration/ai.py`, `backend/app/orchestration/intake_router.py`
- preprocess 필요 여부 판단: `backend/app/modules/preprocess/planner.py`
- analysis question understanding / analysis plan draft: `backend/app/modules/analysis/run_service.py`
- visualization detailed chart planning: `backend/app/modules/visualization/planner.py`

현재는 planner라는 독립 모듈이 없고, 위 로직이 orchestration과 개별 모듈 안에 분산되어 있다.

## Decisions Locked In This Phase

### Planner 모듈 위치

- planner는 독립 모듈로 추가한다.
- 경로는 `backend/app/modules/planner`로 고정한다.
- planner는 orchestration helper가 아니라 재사용 가능한 module layer로 둔다.

### Planner 입력

planner 입력은 아래로 고정한다.

- `user_input`
- `request_context`
- `source_id`
- `dataset_context`
- `guideline_context`
- `model_id`

planner는 dataset RAG retrieval 결과를 기본 입력으로 받지 않는다.

### Planner 출력

planner는 `planning_result`만 반환한다.

`planning_result`는 아래 필드를 반드시 포함한다.

- `route`
- `needs_clarification`
- `clarification_question`
- `preprocess_required`
- `analysis_plan`
- `need_visualization`
- `need_report`
- `guideline_context_used`

### Planner가 흡수하는 책임

| 현재 위치 | planner가 흡수 여부 | 설명 |
| --- | --- | --- |
| `analyze_intent` | 흡수 | 데이터 질문의 상위 분기 판단을 planner로 이동한다. |
| `build_preprocess_decision` | 흡수 | preprocess 필요 여부는 planner가 결정한다. |
| `QuestionUnderstanding` 생성 | 흡수 | 질문 모호성 판단과 clarification 생성은 planner가 맡는다. |
| `AnalysisPlanDraft` 생성 | 흡수 | 최종 analysis plan의 초안 생성까지 planner가 맡는다. |
| clarification 판단 | 흡수 | `needs_clarification`와 질문 문구는 planner가 결정한다. |

### Planner가 흡수하지 않는 책임

| 현재 위치 | planner가 흡수 여부 | 설명 |
| --- | --- | --- |
| preprocess 실행 | 비흡수 | deterministic transform 실행은 preprocess module이 계속 담당한다. |
| analysis code generation | 비흡수 | planner는 code를 만들지 않는다. |
| analysis sandbox execution | 비흡수 | planner는 실행 엔진이 아니다. |
| visualization detailed chart planning | 비흡수 | chart type/x/y 선택은 visualization phase 책임으로 유지한다. |
| report drafting | 비흡수 | report text generation은 reports module 책임으로 유지한다. |

### Phase 2의 배선 범위

- planner 모듈 자체는 이 phase에서 구현한다.
- 기존 intake/preprocess/analysis 경로는 compatibility wrapper를 통해 planner를 점진 도입해도 된다.
- 단, `Phase 3` 이전에는 main workflow의 최종 기본 경로를 완전히 바꾸지 않는다.

## Implementation Changes

### Planner module

- `PlanningResult` schema를 추가한다.
- `PlannerService`를 추가한다.
- planner 내부에서 현재 `analyze_intent`, `preprocess_decision`, `question_understanding`, `analysis plan draft`에 해당하는 판단을 통합한다.
- planner는 최종 `analysis_plan` 초안까지 만든다.

### Analysis integration

- 기존 `AnalysisRunService` 안의 planning 일부는 planner로 이동한다.
- analysis module은 `analysis_plan`을 입력받아 실행과 검증에 집중한다.
- analysis module이 자체 clarification 판단을 새로 만들지 않도록 planner 책임과 겹치지 않게 정리한다.

### Compatibility

- 기존 코드가 한 번에 완전 교체되지 않더라도 planner를 호출하는 adapter를 둘 수 있다.
- 단, planner와 기존 분산 판단 로직이 서로 다른 결정을 동시에 내리는 구조는 허용하지 않는다.
- source of truth는 planner 하나여야 한다.

## Out of Scope

- main workflow 기본 경로의 full rewire
- dataset RAG fallback 정책 확정
- visualization detailed chart planner 제거
- reports downstream 정리

## Completion Criteria

- `backend/app/modules/planner`가 실제 코드에 존재한다.
- planner 입력과 출력 계약이 문서대로 고정된다.
- implementer가 planner가 어디까지 책임지는지 추가 결정을 내릴 필요가 없다.
- visualization chart 상세 추천은 여전히 visualization phase 책임이라고 문서와 코드에서 명시된다.

## Handoff To Next Phase

- `Phase 3`는 planner를 dataset selected path의 단일 상위 결정 지점으로 배선한다.
- `Phase 3`는 planner 출력 `route`를 기준으로 orchestration 재배선을 수행한다.
- `Phase 3`는 planner 입력 evidence를 `guideline_context`로만 고정하고, dataset RAG는 fallback path로만 연결한다.

## Validation Checklist

- 이 문서만 보고 아래 질문에 답할 수 있어야 한다.
- planner는 `analyze_intent`를 대체하는가?
- 답: 그렇다.
- planner는 `preprocess_decision`을 대체하는가?
- 답: 그렇다.
- planner는 `analysis question understanding`과 `analysis plan draft`를 흡수하는가?
- 답: 그렇다.
- planner는 visualization chart type까지 정하는가?
- 답: 아니다. detailed chart planning은 visualization phase 책임이다.
- planner는 code generation을 하는가?
- 답: 아니다. planner는 실행 엔진이 아니다.
