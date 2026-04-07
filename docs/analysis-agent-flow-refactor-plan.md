# Analysis Agent Flow Refactor Plan

## Summary

현재 백엔드는 `analysis`가 핵심 계산 엔진이어야 하는데, 실제 흐름상 `rag`, `visualization`, `reports`가 일부 질문에서 분석을 우회하거나 대체할 수 있는 구조다. 이번 개편의 목적은 정량 질문의 정답 경로를 `analysis`로 고정하고, `guidelines -> rag`는 분석 해석 기준 제공용으로 축소하며, `visualization/reports`를 `analysis_result`의 downstream으로 고정하는 것이다.

최종 기준 Flow는 아래로 확정한다.

`chat -> orchestration -> datasets -> context -> guidelines -> rag -> planner -> preprocess(optional) -> analysis -> visualization(optional) -> reports(optional) -> results`

이 계획은 백엔드 중심 개편이며, 구현 순서는 `공통 입력 정리 -> 계획 결정 단일화 -> 실행 그래프 재배선 -> downstream 정리` 순서로 진행한다.

## Target Architecture

### 1. 모듈 책임 재정의

- `chat`: 질문 수신, 세션/런 관리, 스트리밍, 승인 재개만 담당한다. 비즈니스 판단은 넣지 않는다.
- `orchestration`: 상태 전이와 단계 실행 순서만 담당한다. 질문 해석, 전처리 필요 여부 판단, 차트 추천 같은 판단 로직을 제거한다.
- `datasets`: dataset identity와 lifecycle만 담당한다. `source_id`, 파일 존재 여부, 전처리 후 새 dataset 추적만 제공한다.
- `context` 신규: 데이터셋 사실의 단일 소스. 스키마, dtype, 샘플, 결측률, 시간축 후보, row count, quality summary를 한 번만 계산한다.
- `guidelines`: 활성 guideline 선택과 메타 조회만 담당한다.
- `rag`: guideline retrieval 전용 보조 엔진으로 축소한다. 메인 데이터 QA에서 raw CSV retrieval은 사용하지 않는다.
- `planner` 신규: 질문 해석, clarification, preprocess 필요 여부, analysis plan, visualization/report 필요 여부를 한 번에 결정한다.
- `preprocess`: planner가 승인한 deterministic transform 실행만 담당한다.
- `analysis`: 정량 결과 생성의 단일 엔진. 질문별 계산, 코드 생성/실행, 검증, 저장을 담당한다.
- `visualization`: `analysis_result`를 차트로 바꾸는 표현 계층. 원본 CSV를 다시 해석하지 않는다.
- `reports`: `analysis_result + visualization_result + guideline_context`를 서술형 리포트로 변환한다.
- `results`: 분석/시각화/리포트 산출물의 연결 허브이자 재조회 기준점으로 사용한다.

### 2. 새 내부 계약

#### `dataset_context`

- `source_id`
- `filename`
- `columns`
- `dtypes`
- `numeric_columns`
- `datetime_columns`
- `categorical_columns`
- `sample_rows`
- `missing_rates`
- `row_count_sample`
- `row_count_total`
- `quality_summary`

#### `guideline_context`

- `guideline_source_id`
- `retrieved_chunks`
- `evidence_summary`
- `status`

#### `planning_result`

- `needs_clarification`
- `clarification_question`
- `preprocess_required`
- `preprocess_plan_outline`
- `analysis_plan`
- `need_visualization`
- `need_report`

#### `preprocess_result`

- `status`
- `input_source_id`
- `output_source_id`
- `output_filename`
- `schema_changed`

#### `analysis_result`

- `summary`
- `table`
- `raw_metrics`
- `used_columns`
- `execution_status`

#### `visualization_result`

- `status`
- `chart_type`
- `chart_data`
- `caption`
- `artifact`

#### `report_result`

- `status`
- `summary`
- `report_id`
- `visualizations`

#### `result_refs`

- `analysis_result_id`
- `report_id`
- `source_id`
- `run_id`
- `final_status`

## Detailed Flow

### 1. `chat`

역할:

- 사용자 질문 수신
- 세션/런 ID 생성
- 스트리밍 응답
- 승인/수정/취소 인터랙션 관리

입력:

- `question`
- `session_id`
- `source_id`

출력:

- `run_id`
- 스트리밍 이벤트
- 최종 응답 payload

예시:

- 사용자: `지난 3개월 라인별 평균 불량률 추세를 보여주고 보고서도 작성해줘`
- `chat`은 질문을 해석하지 않고 `orchestration`으로 넘긴다.

이유:

- `chat`이 도메인 판단을 시작하면 이후 `planner`와 중복된다.

### 2. `orchestration`

역할:

- 각 모듈 실행 순서 제어
- 상태 누적
- optional 단계 분기

입력:

- `question`
- `source_id`
- `session_id`

출력:

- 실행 상태 전체
- 각 단계 산출물 연결
- 최종 출력 타입 결정

추천 상태 구조:

- `source_id`
- `target_source_id`
- `dataset_context`
- `guideline_context`
- `planning_result`
- `preprocess_result`
- `analysis_result`
- `visualization_result`
- `report_result`
- `result_refs`

예시:

- 질문이 일반 상식 질문이면 `general answer`로 빠진다.
- 데이터셋 질문이면 무조건 `datasets -> context -> guidelines -> rag -> planner` 순서로 들어간다.
- `planner.preprocess_required == true`면 `preprocess`
- `planner.need_visualization == true`면 `visualization`
- `planner.need_report == true`면 `reports`

이유:

- 흐름 제어만 담당해야 팀이 읽기 쉽다.

### 3. `datasets`

역할:

- 선택된 `source_id`의 데이터셋 존재 여부 보장
- 파일 경로, 메타 정보 조회
- 전처리 후 새 데이터셋 교체 시 `target_source_id` 갱신 기반 제공

입력:

- `source_id`

출력:

- dataset record
- `filename`
- `storage_path`
- `filesize`

예시:

- 사용자가 `sales_2024.csv`를 선택하고 질문
- `datasets`는 해당 데이터셋을 로드 가능한 상태인지 확인한다.

이유:

- 실제 데이터셋 identity는 여기서만 다뤄야 한다.

### 4. `context`

역할:

- 데이터셋 사실 정보를 한 번만 계산
- 이후 `planner`, `preprocess`, `analysis`, `reports`가 공통으로 사용

입력:

- dataset record
- `target_source_id`

출력:

- `dataset_context`

권장 필드:

- `source_id`
- `columns`
- `dtypes`
- `numeric_columns`
- `datetime_columns`
- `categorical_columns`
- `sample_rows`
- `missing_rates`
- `row_count_sample`
- `row_count_total`
- `quality_summary`

예시:

- 컬럼: `date`, `line`, `defect_count`, `production_count`
- `datetime_columns = ["date"]`
- `numeric_columns = ["defect_count", "production_count"]`
- `quality_summary = "production_count 결측 3.2%"`

중요:

- 여기서 만든 정보만 이후 단계가 사용해야 한다.
- `analysis`, `preprocess`, `reports`가 각자 따로 샘플을 읽어 판단하지 않게 한다.

### 5. `guidelines`

역할:

- 현재 활성 guideline 선택
- 질문과 관련 있는 도메인 정책의 출처 제공

입력:

- 현재 활성 guideline
- `question`

출력:

- guideline 메타
- `guideline_source_id`

예시:

- guideline 문서에 `불량률 = defect_count / production_count`
- 또는 `월별 실적은 완료월 기준으로 계산`

이유:

- KPI 정의, 필터 기준, 도메인 해석은 분석 전에 알아야 한다.

### 6. `rag`

역할:

- guideline에서 질문 관련 근거 검색
- 분석 계획 전에 도메인 근거 요약 생성

입력:

- `question`
- guideline source

출력:

- `guideline_context`
- `retrieved_chunks`
- `evidence_summary`

예시:

- 질문: `지난 3개월 불량률 추세`
- retrieval 결과:
  - `불량률 = defect_count / production_count`
  - `current month는 미완료 월이라 제외`
- `evidence_summary`:
  - `불량률은 defect_count/production_count로 계산하고, 최근 3개월은 완료월만 포함해야 합니다.`

중요:

- 여기서는 raw dataset CSV를 검색하지 않는다.
- 정량 답변은 여기서 만들지 않는다.

### 7. `planner`

역할:

- 질문 해석
- clarification 여부 판단
- preprocess 필요 여부 판단
- analysis plan 생성
- visualization/report 필요 여부 판단

입력:

- `question`
- `dataset_context`
- `guideline_context`

출력:

- `planning_result`

권장 필드:

- `needs_clarification`
- `clarification_question`
- `preprocess_required`
- `preprocess_plan_outline`
- `analysis_plan`
- `need_visualization`
- `need_report`

예시 1:

- 질문: `지난 3개월 라인별 평균 불량률 추세를 보여줘`
- 결과:
  - `preprocess_required = false`
  - `analysis_plan = time bucket month + series line + metric avg(defect_rate)`
  - `need_visualization = true`
  - `need_report = false`

예시 2:

- 질문: `온도 컬럼의 'N/A', '-'를 정리하고 결측을 채운 뒤 압력과 불량률 관계를 분석해줘`
- 결과:
  - `preprocess_required = true`
  - `preprocess_plan_outline = parse/clean/impute`
  - `analysis_plan = scatter(pressure, defect_rate)`
  - `need_visualization = true`

예시 3:

- 질문: `좋아 보이는 차트 하나 만들어줘`
- 결과:
  - `needs_clarification = true`
  - `clarification_question = 어떤 지표를 어떤 기준으로 보고 싶은지 알려주세요.`

이유:

- 무엇을 할 것인가는 이 모듈 하나가 결정해야 전체 시스템이 안정적이다.

### 8. `preprocess(optional)`

역할:

- planner가 승인한 transform만 deterministic하게 실행
- 새 데이터셋 생성
- 새 `target_source_id` 반환

입력:

- `target_source_id`
- approved preprocess plan

출력:

- `preprocess_result`
- `output_source_id`
- `output_filename`
- `schema_changed`

예시:

- 입력 데이터:
  - `temperature = ["23.1", "-", "N/A"]`
- 처리:
  - `"-", "N/A" -> NaN`
  - 평균 대체
- 출력:
  - 새 데이터셋 `source_id = processed_xxx`

후속 규칙:

- preprocess가 실행되면 반드시 다시 `context`를 돌린다.

이유:

- 전처리 후 컬럼 상태가 달라졌는데 이전 context로 분석하면 계획이 틀어진다.

### 9. `analysis`

역할:

- 실제 정량 계산
- plan 검증
- 코드 생성/실행
- 결과 검증
- 결과 저장

입력:

- `question`
- 최신 `dataset_context`
- `analysis_plan`
- `guideline_context`

출력:

- `analysis_result`

권장 필드:

- `summary`
- `table`
- `raw_metrics`
- `used_columns`
- `execution_status`

예시 1:

- 질문: `지난 3개월 라인별 평균 불량률 추세`
- 분석 결과:
  - `summary = "A라인은 1.8% -> 2.4%로 상승, B라인은 1.2% -> 1.1%로 안정적입니다."`
  - `table = [{month: "2026-01", line: "A", defect_rate: 0.018}, ...]`
  - `raw_metrics = {worst_line: "A", max_defect_rate: 0.024}`

예시 2:

- 질문: `압력과 불량률 관계 분석`
- 분석 결과:
  - `summary = "압력 증가 구간에서 불량률이 함께 상승하는 경향이 보입니다."`
  - `table = [{pressure: 32.1, defect_rate: 0.011}, ...]`
  - `raw_metrics = {correlation: 0.63}`

중요:

- 이 단계가 시스템의 정답 엔진이다.
- `visualization`, `reports`는 여기 나온 결과만 설명해야 한다.

### 10. `visualization(optional)`

역할:

- `analysis_result.table` 또는 `raw_metrics`를 차트로 변환
- 원본 CSV를 다시 해석하지 않음

입력:

- `analysis_plan`
- `analysis_result`

출력:

- `visualization_result`

권장 필드:

- `chart_type`
- `chart_data`
- `caption`
- `artifact`

예시 1:

- `analysis_plan.visualization_hint = line`
- `table = [{month, line, defect_rate}]`
- 결과:
  - `line chart`
  - `x = month`
  - `series = line`
  - `y = defect_rate`

예시 2:

- `analysis_plan.visualization_hint = scatter`
- `table = [{pressure, defect_rate}]`
- 결과:
  - `scatter chart`
  - `x = pressure`
  - `y = defect_rate`

이유:

- 시각화는 분석 결과의 표현이어야 한다.
- 원본 CSV를 다시 읽어 비슷해 보이는 차트를 만드는 순간 신뢰도가 떨어진다.

### 11. `reports(optional)`

역할:

- 분석 결과를 서술형 리포트로 정리
- 질문에 대한 답, 근거 수치, 차트 해석, 권고안을 생성

입력:

- `question`
- `analysis_result`
- `visualization_result`
- `guideline_context`
- `dataset_context`

출력:

- `report_result`

권장 섹션:

- 요약
- 핵심 인사이트
- 근거 수치
- 시각화 해석
- 권고사항

예시:

- 질문: `지난 3개월 라인별 평균 불량률 추세를 보여주고 보고서도 작성해줘`
- 리포트:
  - 요약: `최근 3개월 동안 A라인의 불량률이 상승했고, B라인은 안정적이었습니다.`
  - 핵심 인사이트: `A라인은 1월 1.8%에서 3월 2.4%로 상승했습니다.`
  - 근거 수치: `최고 불량률은 3월 A라인 2.4%였습니다.`
  - 시각화 해석: `라인 차트에서 A라인 기울기가 가장 가파릅니다.`
  - 권고사항: `A라인 3월 공정 조건과 원자재 변경 이력을 우선 점검해야 합니다.`

중요:

- 보고서는 dataset overview가 아니라 question-specific report여야 한다.

### 12. `results`

역할:

- 실행 결과의 최종 저장 허브
- 분석/시각화/리포트 연결
- 재조회와 후속 질문의 기준점

입력:

- `analysis_result`
- `visualization_result`
- `report_result`
- `run_id`
- `source_id`

출력:

- 저장된 result reference

권장 저장 구조:

- `analysis_result_id`
- `source_id`
- `run_id`
- `analysis_result`
- `chart_data`
- `report_id`
- `final_status`

예시:

- 같은 세션에서 후속 질문:
  - `그럼 A라인만 따로 보여줘`
- `results`를 통해 이전 `analysis_result`를 참조해 재분석할 수 있다.

이유:

- 팀 입장에서 한 실행에서 무엇이 만들어졌는가를 한 곳에서 추적할 수 있어야 한다.

## Implementation Phases

### Phase 1. `context` 모듈 도입

- `backend/app/modules/context`를 신설한다.
- 기존에 분산된 데이터 프로파일링 로직을 `context`로 이동한다.
  - 현재 `preprocess`의 dataset profile 생성
  - 현재 `analysis`의 metadata snapshot 생성
  - 현재 `reports`의 dataset metrics seed 생성
- `context`는 사실 계산만 담당하고, 질문 해석은 하지 않는다.
- `row_count_total`은 가능하면 전체 기준으로 계산하고, 어려우면 샘플 기반 값과 명확히 구분해 저장한다.

완료 기준:

- 이후 모듈이 직접 샘플을 읽어 schema/dtype/missing을 계산하지 않고 `dataset_context`를 사용한다.
- 동일 dataset에 대해 `preprocess`, `analysis`, `reports`가 같은 컬럼/타입 판단을 공유한다.

### Phase 2. `planner` 모듈 신설

- `backend/app/modules/planner`를 신설한다.
- 아래 판단을 planner로 모은다.
  - 질문이 모호한지
  - preprocess가 필요한지
  - analysis plan이 무엇인지
  - visualization/report가 필요한지
- 기존 분산 로직을 정리한다.
  - `orchestration.ai.analyze_intent`는 planner 내부로 흡수
  - `preprocess.planner.build_preprocess_decision`의 필요 여부 판단은 planner로 이동
  - `analysis.run_service`의 질문 해석 및 plan draft 생성은 planner가 호출하되, 상세 codegen은 `analysis`에 유지
- planner 입력은 반드시 `question + dataset_context + guideline_context` 조합으로 고정한다.
- planner는 실행하지 않고 결정만 반환한다.

완료 기준:

- `preprocess_required`, `analysis_plan`, `need_visualization`, `need_report`가 planner 단일 결과로 나온다.
- orchestration이 질문 의미를 직접 해석하지 않는다.

### Phase 3. `orchestration` 그래프 재배선

- `orchestration/workflows/context.py`, `planner.py`를 추가한다.
- 메인 그래프를 아래 순서로 재배선한다.
  - `chat -> orchestration -> datasets -> context -> guidelines -> rag -> planner`
  - `planner.preprocess_required == true`면 `preprocess`
  - `preprocess` 완료 후 `target_source_id` 갱신
  - 갱신 후 반드시 `context` 재실행
  - 이후 `analysis`
  - 이후 `visualization`과 `reports`는 planner 플래그 기반 optional
  - 마지막 `results`
- 기존 `dataset_qa -> rag_flow` 직접 경로는 제거한다.
- 일반 상식 질문만 `general answer`로 빠지고, dataset이 선택된 정량 질문은 기본적으로 `analysis`까지 도달하게 한다.

완료 기준:

- 메인 데이터 질문 경로가 `analysis`를 우회하지 않는다.
- preprocess가 실행되면 새 source 기준으로 이후 단계가 동작한다.

### Phase 4. `guidelines -> rag`를 planning input으로 고정

- guideline retrieval은 analysis 이후가 아니라 planning 전에 실행되도록 고정한다.
- `rag`는 dataset raw text retrieval이 아니라 guideline evidence retrieval만 담당한다.
- `guideline_context.evidence_summary`는 planner와 analysis 입력으로 전달한다.
- guideline이 없으면 빈 컨텍스트로 진행하되, fallback policy는 단순하게 유지한다.

완료 기준:

- KPI 정의, 용어 해석, 집계 기준이 analysis plan 생성 전에 반영된다.
- `rag`가 정량 정답 생성 경로에서 빠진다.

### Phase 5. `preprocess`를 executor로 단순화

- `preprocess`는 planner가 넘긴 outline 또는 승인된 연산 계획만 실행한다.
- preprocess 자체가 해야 할지 말지를 다시 판단하지 않는다.
- 실행 결과로 `output_source_id`, `output_filename`, `schema_changed`, `status`를 반환한다.
- preprocess 후 context refresh를 orchestration 레벨에서 강제한다.

완료 기준:

- preprocess는 deterministic transform executor 역할만 수행한다.
- preprocess 후 analysis가 항상 최신 dataset_context를 본다.

### Phase 6. `analysis`를 정답 엔진으로 고정

- `analysis` 입력을 `question + latest dataset_context + analysis_plan + guideline_context`로 확정한다.
- 질문 해석/plan 생성은 planner가 맡고, analysis는 승인된 plan 실행에 집중한다.
- codegen, validation, sandbox, result persistence는 유지하되, prompt 입력에 guideline evidence를 포함시킨다.
- `analysis_result`는 계속 `summary`, `table`, `raw_metrics`, `used_columns`, `execution_status` 중심으로 유지한다.

완료 기준:

- 정량 답변은 항상 analysis execution 결과를 바탕으로 생성된다.
- downstream이 analysis 결과를 신뢰 가능한 기준점으로 사용한다.

### Phase 7. `visualization`을 analysis downstream으로 고정

- 메인 파이프라인에서 visualization은 `analysis_result`가 있을 때만 실행한다.
- 자동 visualization은 `analysis_plan.visualization_hint + analysis_result.table/raw_metrics`만 사용한다.
- 원본 CSV를 다시 읽어서 chart를 생성하는 기존 auto path는 메인 Flow에서 제거한다.
- 필요하면 별도 `manual_viz` 또는 `EDA` API로 분리하되, 메인 분석 Flow에는 포함하지 않는다.

완료 기준:

- 분석 없는 차트 생성이 메인 경로에서 사라진다.
- visualization은 analysis 표현 계층으로만 동작한다.

### Phase 8. `reports`를 question-specific report로 전환

- report draft 생성 입력을 `analysis_result`, `visualization_result`, `guideline_context`, `dataset_context`로 바꾼다.
- 기존 dataset overview 성격의 샘플 통계는 보조 정보로만 남긴다.
- report 템플릿은 아래 순서를 기본으로 고정한다.
  - 질문에 대한 직접 답
  - 핵심 인사이트
  - 근거 수치
  - 시각화 해석
  - 권고사항
- report는 analysis 없이 독립 생성되지 않도록 메인 Flow를 제한한다.

완료 기준:

- report 내용이 질문별 분석 결과를 직접 반영한다.
- 데이터셋 개요 리포트와 질문 기반 분석 리포트가 구분된다.

### Phase 9. `results`를 실행 산출물 허브로 확장

- `results`는 analysis 결과뿐 아니라 visualization/report 참조도 묶어서 관리한다.
- 최소 저장 연결은 아래로 고정한다.
  - `run_id`
  - `source_id`
  - `analysis_result_id`
  - `chart_data` 또는 chart ref
  - `report_id`
  - `final_status`
- 후속 질문은 `results`를 기반으로 직전 실행 결과를 참조할 수 있게 한다.

완료 기준:

- 한 번의 run에서 생성된 분석/차트/리포트를 한곳에서 추적할 수 있다.
- 후속 질문 시 재조회 기준점이 명확하다.

## API / Interface Changes

- 외부 API 경로는 가능하면 유지한다.
- 내부 상태와 서비스 인터페이스는 아래 방향으로 바꾼다.
- `orchestration` 상태에 `dataset_context`, `guideline_context`, `planning_result`, `result_refs`를 추가한다.
- `analysis` 서비스는 raw metadata 대신 `dataset_context`와 `analysis_plan`을 입력으로 받게 정리한다.
- `visualization` 서비스는 원칙적으로 `analysis_result` 기반 생성 메서드만 메인 경로에서 사용한다.
- `reports` 서비스는 `build_report_draft(question, analysis_result, visualization_result, guideline_context, dataset_context, ...)` 형태로 전환한다.
- `results` repository는 analysis 결과 저장 외에 run 단위 참조 저장을 지원한다.

## Test Plan

### 핵심 시나리오

- 정량 질문 기본 경로
  - dataset 선택 후 집계 질문을 하면 `analysis`가 실행되고 `rag`가 정답 생성에 사용되지 않는다.
- guideline 반영 경로
  - KPI 정의가 guideline에 있을 때 analysis plan과 summary에 반영된다.
- preprocess 경로
  - planner가 preprocess를 요구하면 preprocess 후 새 `target_source_id`로 context refresh가 일어난다.
- clarification 경로
  - 모호한 질문은 preprocess/analysis로 가지 않고 clarification 질문으로 종료된다.
- visualization 경로
  - `analysis_result`가 없는 경우 메인 Flow에서 visualization이 생성되지 않는다.
  - `analysis_result`가 있으면 그 table 기반으로 차트가 생성된다.
- report 경로
  - report가 `analysis_result` 요약과 `raw_metrics`를 실제로 반영한다.
  - analysis 없이 report-only가 메인 Flow에서 생성되지 않는다.
- results 경로
  - 한 run의 analysis/chart/report 참조가 모두 저장되고 재조회 가능하다.

### 회귀 시나리오

- 기존 chat stream이 세션/런 ID를 유지하는지
- preprocess approval / visualization approval / report approval 인터럽트가 계속 동작하는지
- analysis sandbox와 result persistence가 깨지지 않는지
- dataset 미선택 일반 질문이 여전히 일반 답변 경로로 가는지

## Assumptions And Defaults

- 이번 계획은 백엔드 우선 개편이며, 프론트는 기존 API 경로를 최대한 유지하는 방향으로 나중에 맞춘다.
- 메인 Flow에서는 raw dataset RAG를 제거하고 guideline retrieval만 유지한다.
- `planner`와 `context`는 신규 `modules`로 추가한다.
- `visualization`의 원본 CSV 기반 자동 차트는 메인 분석 Flow에서 제외한다. 필요 시 별도 EDA/manual 기능으로 남긴다.
- `report`는 분석 결과 없는 standalone 문서 생성기가 아니라, analysis downstream 문서화 계층으로 본다.
- 구현은 Phase 1부터 순차적으로 진행하며, 각 Phase 완료 후 바로 다음 단계로 넘어간다. 중간 단계에서 구조를 혼합 운영하지 않는다.
