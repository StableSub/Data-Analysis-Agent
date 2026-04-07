# Analysis Agent Flow Overview

## Purpose

이 디렉터리는 기존 단일 계획 문서를 `공통 기준 문서 + phase별 실행형 문서`로 분리한 기준선이다.

- 이 문서는 모든 phase가 공유하는 현재 baseline, 목표 flow, 공통 계약, phase 순서를 정의한다.
- 실제 AI 주입 단위는 개별 `phase-*.md` 문서다.
- 개별 phase 문서는 단독으로 구현 결정을 내릴 수 있어야 하며, 공통 계약 이름만 이 문서를 참조한다.

## Current Baseline

현재 코드 기준 실제 모듈 구성은 아래와 같다.

- `chat`
- `orchestration`
- `datasets`
- `profiling`
- `eda`
- `guidelines`
- `rag`
- `preprocess`
- `analysis`
- `visualization`
- `reports`
- `results`

현재 기본 흐름은 아래에 가깝다.

```text
chat
-> orchestration
-> no dataset: general question terminal
-> dataset selected:
   - dataset_qa -> rag -> guideline(optional) -> visualization(optional) -> merge_context -> report(optional) | final answer
   - data_pipeline -> preprocess(profile/eda support) -> analysis | rag -> guideline(optional) -> visualization(optional) -> merge_context -> report(optional) | final answer
```

현재 코드 기준 핵심 사실은 아래와 같다.

- 데이터셋이 선택되지 않았으면 일반 질의 경로로 종료된다.
- 데이터셋이 선택되면 intake 결과에 따라 `dataset_qa` 또는 `data_pipeline`으로 분기한다.
- `dataset_qa`는 기본적으로 dataset RAG 경로로 들어간다.
- `data_pipeline`은 전처리 이후 `analysis` 또는 `rag`로 이어진다.
- `guideline_rag`는 이미 orchestration에 연결되어 있지만, planning 전 공통 입력 계층으로는 아직 재배선되지 않았다.
- `preprocess`는 이미 profiling 기반 profile을 사용한다.
- `analysis`는 아직 직접 CSV 샘플을 읽어 metadata를 만든다.
- `reports`는 아직 직접 CSV를 다시 읽어 metrics를 만든다.

현재 baseline을 확인할 때 우선 참고할 코드 위치는 아래다.

- `backend/app/orchestration/builder.py`
- `backend/app/orchestration/intake_router.py`
- `backend/app/modules/profiling/service.py`
- `backend/app/modules/preprocess/service.py`
- `backend/app/modules/analysis/service.py`
- `backend/app/modules/reports/service.py`

## Target Flow

목표 기본 경로는 아래로 고정한다.

```text
chat
-> orchestration
-> no dataset: general question terminal
-> dataset selected:
   -> dataset_context
   -> guideline_context
   -> planner
   -> preprocess(optional)
   -> analysis (default) | fallback_rag (exception only)
   -> optional downstream outputs:
      - visualization
      - report
      - final answer
   -> results
```

목표 상태에서 중요한 원칙은 아래다.

- 정량 질문의 정답 엔진은 `analysis` 하나로 고정한다.
- planning 전에 들어가는 evidence는 `guidelines + guideline_rag`가 만든 `guideline_context`다.
- dataset RAG는 planning의 기본 입력이 아니다.
- dataset RAG는 `Phase 3` 이후에도 legacy compatibility/fallback retrieval path로만 유지한다.
- `eda`는 메인 직렬 단계가 아니라 side capability로 유지한다.
- `visualization`과 `reports`는 `analysis_result` 기반 downstream 계층으로 고정한다.

## Shared Contracts

### `dataset_context`

`dataset_context`는 별도 현재 모듈명이 아니라 공통 계약 이름이다. 구현은 `profiling` 기반 provider가 맡는다.

- `source_id`
- `filename`
- `available`
- `row_count_total`
- `row_count_sample`
- `column_count`
- `columns`
- `dtypes`
- `logical_types`
- `type_columns`
- `numeric_columns`
- `datetime_columns`
- `categorical_columns`
- `boolean_columns`
- `identifier_columns`
- `group_key_columns`
- `sample_rows`
- `missing_rates`
- `quality_summary`

`quality_summary`는 아래 최소 구조를 갖는다.

- `missing_total`
- `missing_ratio`
- `top_missing_columns`

`quality_summary`는 LLM 요약이 아니라 profiling 결과에서 결정적으로 계산 가능한 품질 요약만 담는다.

### `guideline_context`

- `guideline_source_id`
- `guideline_id`
- `filename`
- `status`
- `retrieved_chunks`
- `retrieved_count`
- `has_evidence`
- `evidence_summary`

### `planning_result`

- `route`
- `needs_clarification`
- `clarification_question`
- `preprocess_required`
- `analysis_plan`
- `need_visualization`
- `need_report`
- `guideline_context_used`

`planning_result.route`는 아래만 허용한다.

- `general_question`
- `analysis`
- `fallback_rag`

### `analysis_result`

- `summary`
- `table`
- `raw_metrics`
- `used_columns`
- `execution_status`
- `analysis_result_id`

### `visualization_result`

- `status`
- `chart_type`
- `chart_data`
- `caption`
- `artifact`

### `report_result`

- `status`
- `summary`
- `report_id`
- `visualizations`

## Phase Sequence

### Phase 1. Dataset Context

- `profiling` 기반 `dataset_context`를 공통 계약으로 도입한다.
- `analysis`를 먼저 이 계약으로 전환한다.

### Phase 2. Planner

- 분산된 판단 로직을 `planning_result`로 통합한다.
- 단, orchestration 기본 배선은 아직 바꾸지 않는다.

### Phase 3. Orchestration Rewire

- `dataset_qa -> rag` 기본 경로를 줄이고, dataset selected path를 planner 중심으로 재배선한다.
- planning 전 evidence 입력을 `guideline_context`로 고정한다.

### Phase 4. Analysis-First Downstream

- `visualization`과 `reports`를 `analysis_result` 기반 downstream으로 고정한다.
- `reports`의 direct CSV reread를 종료한다.

## Cross-Phase Invariants

- 데이터셋이 선택되지 않은 일반 질의 경로는 모든 phase에서 유지한다.
- `planner`는 detailed visualization chart planning을 흡수하지 않는다.
- `guideline_context`는 planning 전 evidence provider다.
- dataset RAG는 기본 planner 입력이 아니다.
- `analysis`는 `Phase 3` 이후 정량 답변의 기본 엔진이어야 한다.
- `reports`는 `Phase 4` 완료 후 direct CSV reread에 의존하지 않아야 한다.

## How To Use These Docs

- AI에 구현을 주입할 때는 `00-overview.md`를 먼저 읽고, 필요한 `phase-*.md` 하나만 추가로 주입한다.
- phase 문서만 읽어도 구현 결정을 내릴 수 있어야 한다.
- phase 문서와 overview가 충돌하면 phase 문서의 결정이 우선한다.
