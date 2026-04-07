# Phase 4. Analysis-First Downstream

## Summary

이 phase의 목표는 `visualization`과 `reports`를 `analysis_result` 기반 downstream 계층으로 고정하는 것이다.

이 phase에서 `reports`는 direct CSV reread를 중단한다.

## Current State

현재 downstream 상태는 아래와 같다.

- `visualization`은 `analysis_result`가 있으면 이를 직접 소비할 수 있지만, 아직 phase 수준의 강제 정책으로 고정되지는 않았다.
- `reports`는 `build_metrics_for_source()`에서 원본 CSV를 다시 읽어 metrics를 만든다.
- `report_draft`는 현재 `insight_summary`, `visualization_summary`, 직접 계산한 dataset metrics를 함께 사용한다.

현재 확인 기준 코드는 아래다.

- `backend/app/orchestration/workflows/visualization.py`
- `backend/app/modules/visualization/service.py`
- `backend/app/orchestration/workflows/report.py`
- `backend/app/modules/reports/service.py`

## Decisions Locked In This Phase

### Visualization 정책

- `analysis_result`와 `analysis_plan`이 있으면 visualization은 그것을 기본 입력으로 사용한다.
- 이 경우 visualization은 새 dataset-level chart intent planning을 다시 하지 않는다.
- 사용자가 명시적으로 visualization revision을 요청한 경우에만 visualization phase 안에서 limited replanning을 허용한다.

### Reports 정책

- reports 입력은 아래로 고정한다.
- `analysis_result`
- `visualization_result`
- `guideline_context`
- `dataset_context`

- reports는 더 이상 원본 CSV를 다시 읽어 metrics를 계산하지 않는다.
- reports는 `source_id`를 직접 데이터 읽기 키로 사용하지 않고, 필요한 구조적 사실은 `dataset_context`에서 받는다.
- reports에 필요한 정량 결과는 `analysis_result.raw_metrics`와 `analysis_result.table`에서 받는다.

### Metrics 재구성 정책

- 기존 `build_metrics_for_source()`류의 dataset reread 기반 metrics 계산은 종료 대상이다.
- 리포트용 요약 metrics는 아래 우선순위로 구성한다.
- 1순위: `analysis_result.raw_metrics`
- 2순위: `analysis_result.table`
- 3순위: `dataset_context.quality_summary`

### Final answer 정책

- final answer와 report draft는 모두 `analysis_result`를 중심 축으로 사용하는 downstream outputs다.
- final answer가 report의 후행 단계라고 가정하지 않는다.
- guideline evidence와 visualization은 설명 보강용 downstream 입력이다.
- dataset RAG retrieval 결과는 이 phase에서 리포트의 기본 입력으로 승격하지 않는다.

## Implementation Changes

### Visualization

- visualization workflow에서 `analysis_result + analysis_plan`이 있으면 표현 계층으로 바로 진입하도록 정책을 고정한다.
- analysis-generated visualization path를 기본 경로로 삼고, dataset-only visualization planning은 예외 경로로 남긴다.

### Reports

- `ReportService.build_report_draft()` 입력을 `source_id` 중심에서 result/context 중심으로 바꾼다.
- `ReportService.build_metrics_for_source()`와 direct CSV reread 로직은 제거하거나 deprecated compatibility path로 숨긴다.
- report workflow는 필요한 context를 upstream state에서 직접 받는다.

### Orchestration state

- merged context와 report drafting 입력에 `dataset_context`, `guideline_context`, `analysis_result`, `visualization_result`가 모두 포함되도록 정리한다.
- report draft 생성 시 dataset repository reread를 전제로 하지 않는다.
- final answer와 report는 둘 다 upstream analysis 결과를 소비하는 sibling downstream outputs로 유지한다.

## Out of Scope

- planner 책임 재조정
- dataset selected 기본 경로 재배선
- dataset RAG fallback 정책 변경
- analysis execution 엔진 자체 변경

## Completion Criteria

- visualization이 `analysis_result` 기반 downstream 계층으로 고정된다.
- reports가 `analysis_result + visualization_result + guideline_context + dataset_context`를 사용한다.
- reports는 직접 CSV reread metrics 계산을 중단한다.
- downstream이 원본 CSV를 다시 읽지 않아도 답변/리포트 생성이 가능하다.

## Handoff To Next Phase

- 이 phase가 끝나면 별도 후속 phase 없이 target architecture의 `analysis-first downstream` 원칙이 만족된다.
- 이후 작업은 성능 최적화나 호환성 제거처럼 cleanup 성격이어야 하며, 기본 경로 구조를 다시 흔들지 않는다.

## Validation Checklist

- 이 문서만 보고 아래 질문에 답할 수 있어야 한다.
- reports는 언제 CSV reread를 중단하는가?
- 답: 이 phase에서 중단한다.
- visualization은 `analysis_result`가 있으면 planning을 생략하는가?
- 답: 그렇다. 기본적으로 표현 계층으로 바로 진입한다.
- final answer가 report 이후에만 생성되는가?
- 답: 아니다. 둘 다 `analysis_result` 기반 downstream outputs다.
- reports 기본 입력은 무엇인가?
- 답: `analysis_result`, `visualization_result`, `guideline_context`, `dataset_context`다.
- dataset RAG retrieval이 report 기본 입력으로 들어가는가?
- 답: 아니다.
