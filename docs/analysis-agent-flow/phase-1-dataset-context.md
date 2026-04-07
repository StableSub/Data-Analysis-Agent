# Phase 1. Dataset Context

## Summary

이 phase의 목표는 `profiling` 기반 `dataset_context`를 공통 계약으로 도입하고, `analysis`가 더 이상 직접 CSV 샘플을 읽어 planning metadata를 계산하지 않도록 정렬하는 것이다.

이 phase에서 `analysis`는 full cutover 대상이다. `reports`는 이 phase에서 full cutover하지 않는다.

## Current State

현재 기준 상태는 아래와 같다.

- `PreprocessService.build_dataset_profile()`는 이미 `DatasetProfileService`를 사용한다.
- `AnalysisService.build_dataset_metadata()`는 아직 직접 CSV 샘플을 읽고 `MetadataSnapshot`을 만든다.
- `ReportService.build_metrics_for_source()`는 아직 직접 CSV를 읽어 metrics를 만든다.
- `profiling`에는 `DatasetProfileService`만 있고, `dataset_context`라는 공통 계약 provider는 아직 없다.

현재 확인 기준 코드는 아래다.

- `backend/app/modules/profiling/service.py`
- `backend/app/modules/preprocess/service.py`
- `backend/app/modules/analysis/service.py`
- `backend/app/modules/reports/service.py`

## Decisions Locked In This Phase

### 계약과 책임

- `dataset_context` provider는 `profiling` 계층 안에 둔다.
- 이 phase에서는 별도 `context` 모듈을 만들지 않는다.
- 구현 단위는 `DatasetContext` schema와 `DatasetContextService`로 고정한다.

### `dataset_context` 구성 방식

- `DatasetContextService.build_context(source_id)`가 아래 정보를 조합해 반환한다.
- dataset identity 메타: dataset repository
- 구조/타입/샘플/결측률: `DatasetProfileService`
- `quality_summary`: profiling 결과에서 결정적으로 계산 가능한 요약

`quality_summary`는 아래만 포함한다.

- `missing_total`
- `missing_ratio`
- `top_missing_columns`

`quality_summary`를 만들기 위해 EDA LLM 요약이나 AI summary를 호출하지 않는다.

### Analysis cutover 범위

- `analysis`는 이 phase 종료 시 `dataset_context`만을 planning 입력의 사실 원천으로 사용한다.
- `analysis` 내부에서 기존 `MetadataSnapshot` 타입을 유지하는 것은 허용한다.
- 단, `MetadataSnapshot`은 `dataset_context`를 변환한 내부 compatibility shape여야 한다.
- `AnalysisService`는 더 이상 직접 CSV 샘플을 읽어 planning metadata를 계산하지 않는다.

### Preprocess와 Reports 처리

- `preprocess`는 현재 동작을 유지한다.
- `preprocess`를 `dataset_context`로 완전히 재작성하지 않는다.
- `reports`는 이 phase에서 full cutover하지 않는다.
- `reports` direct CSV reread 제거는 `Phase 4` 책임으로 넘긴다.

## Implementation Changes

### Profiling

- `DatasetContext` schema를 추가한다.
- `DatasetContextService`를 추가한다.
- `DatasetContextService`는 dataset repository와 `DatasetProfileService`를 사용해 `dataset_context`를 구성한다.
- `quality_summary`는 `column_profiles`, `missing_rates`, `row_count_total` 기반으로 계산한다.

### Dependencies

- `DatasetContextService` 의존성 생성 함수를 추가한다.
- orchestration과 analysis가 같은 provider를 재사용할 수 있게 dependency wiring을 만든다.

### Analysis

- `AnalysisService`에 `DatasetContextService`를 주입한다.
- 기존 `build_dataset_metadata()`의 direct CSV sample read 로직은 제거하거나 내부 adapter로 축소한다.
- `question_understanding`과 `analysis_plan_draft`에 넘기는 구조적 사실은 `dataset_context`에서만 온다.
- sandbox execution 단계의 실제 dataset file read는 계속 허용한다. 이 phase의 범위는 planning metadata 정렬이다.

### Docs / Contracts

- 이후 phase가 `dataset_context`를 공통 계약으로 사용할 수 있도록 필드 이름을 overview와 일치시킨다.

## Out of Scope

- planner 도입
- orchestration 재배선
- dataset RAG 경로 변경
- reports의 direct CSV reread 제거
- visualization downstream 정리

## Completion Criteria

- `dataset_context` provider가 실제 코드에 존재한다.
- `analysis` planning 입력이 profiling 기반 `dataset_context` 하나로 정렬된다.
- `AnalysisService`는 planning metadata를 위해 직접 CSV sample metadata를 계산하지 않는다.
- `preprocess`는 기존 동작을 유지한다.
- `reports`는 아직 기존 동작을 유지한다.

## Handoff To Next Phase

- `Phase 2`는 `dataset_context`를 planner 입력의 구조적 사실 원천으로 사용한다.
- `Phase 2`는 `analysis` planning을 planner로 이동하더라도 `dataset_context` 필드 이름을 바꾸지 않는다.
- `reports` cutover는 아직 남아 있으므로 planner가 reports downstream 입력을 설계할 때 `dataset_context`와 `analysis_result`를 함께 고려해야 한다.

## Validation Checklist

- 이 문서만 보고 아래 질문에 답할 수 있어야 한다.
- analysis는 이 phase에서 profiling 기반 `dataset_context`로 완전히 전환되는가?
- 답: 그렇다. planning metadata의 직접 CSV 계산은 종료한다.
- reports는 이 phase에서 같이 전환되는가?
- 답: 아니다. `Phase 4`에서 전환한다.
- `quality_summary`는 EDA AI summary를 쓰는가?
- 답: 아니다. profiling 결과로 결정적으로 계산한다.
- `MetadataSnapshot` 타입은 즉시 삭제해야 하는가?
- 답: 아니다. 내부 compatibility shape로 남길 수 있지만, source of truth는 `dataset_context`여야 한다.
