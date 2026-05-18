# raw 제조 데이터셋 기반 프로젝트 평가 지표 활용 분석

작성일: 2026-05-18  
대상 데이터: `backend/evaluation/raw/`  
대상 프로젝트: CSV 기반 데이터 분석 AI Agent Workbench/FastAPI/LangGraph 런타임

## 1. 목적과 결론

이 문서는 `backend/evaluation/raw/`에 있는 제조 공정 CSV들을 우리 프로젝트의 **시나리오 데이터**로 보고, 프로젝트 결과를 어떤 **정량 지표**와 **그래프**로 평가할 수 있는지 정리한다.

핵심 결론은 다음과 같다.

1. 현재 raw 데이터셋은 단순 모델 학습용 데이터라기보다, 우리 프로젝트의 end-to-end 기능을 검증하는 **benchmark scenario oracle**로 쓰는 것이 가장 적합하다.
2. `moldset_labeled.csv`는 현재 가장 좋은 canonical benchmark다. 라벨 분포, 제품별 불량률, 불량 사유별 건수처럼 raw CSV에서 정답을 직접 계산할 수 있어 분석 답변 정확도와 근거 품질을 평가할 수 있다.
3. `moldset_labeled_cn7.csv`, `moldset_labeled_rg3.csv`, `moldset_unlabeled_cn7.csv`, `moldset_unlabeled_rg3.csv`는 평균 0, 표준편차 1에 가까운 scaled-like 데이터로, 스케일링 감지, 전처리 라우팅, 보호 컬럼 위반 여부, 대용량 성능 회귀를 평가하기 좋다.
4. `unlabeled_data.csv`와 unlabeled moldset 파일들은 `PassOrFail`이 없기 때문에 불량률 질문에 대해 “계산 불가”로 답해야 하는 **answerability negative case**로 쓰기 좋다.
5. “정확도”는 ML 분류 정확도 하나로 정의하면 안 된다. 이 프로젝트에서는 route accuracy, column grounding F1, numeric consistency, evidence coverage, answerability accuracy, hallucination rate, protected column violation rate 같은 **agent 실행 품질 지표**로 쪼개야 한다.
6. “속도 개선”은 trace/logging 이벤트와 benchmark runner를 이용해 end-to-end latency, stage latency, time-to-first-event, rows/sec, p50/p95 latency, baseline 대비 개선율로 표현할 수 있다.
7. 그래프는 route confusion matrix, 지표별 bar chart, stage latency stacked bar, row count 대비 latency scatter, p50/p95 추세선, scenario heatmap을 우선 만들면 제품 개선 효과를 설득력 있게 보여줄 수 있다.

## 2. 프로젝트 기준 평가 대상

현재 프로젝트는 자연어 질문을 받아 데이터셋 선택 여부와 질문 의도에 따라 workflow를 실행한다. 평가 지표는 아래 단계별 결과를 기준으로 잡는 것이 좋다.

| 평가 대상 | 프로젝트 기준 파일/계층 | 평가해야 할 질문 |
|---|---|---|
| dataset 선택/입력 | `backend/app/orchestration/intake_router.py`, chat 진입 | 선택된 `source_id`가 workflow state에 들어갔는가? |
| dataset context/profile | profiling, EDA, dataset reader | raw CSV의 행/열/컬럼/타입/라벨 분포가 context에 정확히 반영되는가? |
| planner route | `backend/app/modules/planner/*`, `backend/app/orchestration/builder.py` | 분석/전처리/RAG/시각화/리포트 route가 질문 의도와 맞는가? |
| preprocess approval | `backend/app/orchestration/workflows/preprocess.py` | 표준화 요청은 approval로 멈추고 보호 컬럼을 제외하는가? |
| analysis execution | `backend/app/modules/analysis/*` | raw CSV ground truth와 같은 숫자/표/사용 컬럼을 생성하는가? |
| merge/final answer | `backend/app/orchestration/ai.py`, `builder.py` | 최종 답변에 근거 패키지, answer quality, 계산 숫자가 포함되는가? |
| visualization/report | visualization/report module | 그래프/리포트 요청 시 artifact가 생성되는가? |
| trace/logging | `backend/app/core/trace_logging.py`, `backend/app/orchestration/client.py` | 단계별 이벤트와 최종 상태가 추적 가능하며 속도 지표 계산이 가능한가? |

현재 graphify report 기준으로 관련 핵심 노드는 `AnalysisProcessor`, `EDAService`, `DatasetRepository`, `AnalysisService`, `AnalysisPlan`, `AnalysisExecutionResult`, `AgentClient` 계열이다. 따라서 평가 지표는 단순 LLM 답변 문장만 보지 말고, 이 노드들이 만든 route/state/result/evidence까지 함께 봐야 한다.

## 3. raw 데이터셋 인벤토리

아래 값은 현재 로컬 `backend/evaluation/raw/*.csv`를 직접 읽어 확인한 기준이다.

| 파일 | 행 | 열 | 라벨 | 라벨/불량 기준 | 주요 용도 |
|---|---:|---:|---|---|---|
| `moldset_labeled.csv` | 2,607 | 47 | 있음 | `PassOrFail`: `0` 정상 2,555 / `1` 불량 52, 불량률 1.9946% | canonical 분석 정답 oracle, 제품별/사유별 집계, 전처리 보호 컬럼 검증 |
| `labeled_data.csv` | 7,996 | 45 | 있음 | `PassOrFail`: `Y` 정상 7,925 / `N` 불량 71, 불량률 0.8879% | 라벨 값 표현이 다른 raw dataset 호환성, 라벨 정규화 평가 |
| `supervised_label_cn7.csv` | 6,736 | 26 | 있음 | `PassOrFail`: `0` 정상 6,697 / `1` 불량 39, 불량률 0.5790% | CN7 raw-scale supervised 데이터, 모델/분석 확장 후보 |
| `moldset_labeled_cn7.csv` | 1,211 | 26 | 있음 | `0` 정상 1,194 / `1` 불량 17, 불량률 1.4038% | scaled-like 감지, CN7 subset 평가, preprocessing route 평가 |
| `moldset_labeled_rg3.csv` | 1,182 | 26 | 있음 | `0` 정상 1,157 / `1` 불량 25, 불량률 2.1151% | scaled-like 감지, RG3 subset 평가, CN7/RG3 비교 시나리오 |
| `unlabeled_data.csv` | 795,315 | 46 | 없음 | `PassOrFail` 없음 | 대용량 성능, answerability negative, 라벨 없는 데이터에서 hallucination 방지 |
| `moldset_unlabeled_cn7.csv` | 35,239 | 25 | 없음 | `PassOrFail` 없음 | scaled-like 대용량 CN7 negative/performance case |
| `moldset_unlabeled_rg3.csv` | 35,941 | 25 | 없음 | `PassOrFail` 없음 | scaled-like 대용량 RG3 negative/performance case |

### 3.1 scaled-like 데이터 구분

`Injection_Time`, `Filling_Time`, `Plasticizing_Time`, `Cycle_Time` 네 컬럼을 기준으로 보면 다음과 같이 나뉜다.

| 파일 | 평균/표준편차 성격 | 평가 의미 |
|---|---|---|
| `moldset_labeled.csv` | raw value. 예: `Cycle_Time` 평균 약 60.54, 표준편차 약 1.13 | “표준화가 필요한가?” 질문에서 raw-scale로 판단해야 함 |
| `labeled_data.csv` | raw value. 예: `Injection_Time` 평균 약 8.24, 표준편차 약 3.11 | raw-scale ingestion/EDA 평가 |
| `supervised_label_cn7.csv` | raw value. 예: `Cycle_Time` 평균 약 59.55 | CN7 raw-scale supervised 확장 |
| `moldset_labeled_cn7.csv` | 평균 거의 0, 표준편차 약 1.0004 | 이미 스케일링된 데이터로 판단해야 함 |
| `moldset_labeled_rg3.csv` | 평균 거의 0, 표준편차 약 1.0004 | 이미 스케일링된 데이터로 판단해야 함 |
| `moldset_unlabeled_cn7.csv` | 평균 거의 0, 표준편차 약 1.0000 | 대용량 scaled-like negative/performance |
| `moldset_unlabeled_rg3.csv` | 평균 거의 0, 표준편차 약 1.0000 | 대용량 scaled-like negative/performance |
| `unlabeled_data.csv` | raw value. 예: `Cycle_Time` 평균 약 58.03, 표준편차 약 16.92 | 대용량 raw-scale performance/answerability |

따라서 “스케일링 여부 확인”은 단순 답변 품질이 아니라 EDA/profile 기반 판단 정확도를 측정하는 좋은 benchmark다.

## 4. 이미 존재하는 평가 자산

현재 repository에는 이미 benchmark 기초가 존재한다.

| 위치 | 현재 역할 |
|---|---|
| `backend/evaluation/cases/manufacturing_analysis_cases.jsonl` | analysis route 질문과 기대 route/컬럼/evidence 정의 |
| `backend/evaluation/cases/manufacturing_preprocess_cases.jsonl` | standardize/scale 요청과 보호 컬럼/대상 컬럼 정의 |
| `backend/evaluation/cases/manufacturing_answer_cases.jsonl` | 최종 답변에 들어가야 할 숫자/표/금지 표현 정의 |
| `backend/evaluation/docs/benchmark-case-guide.md` | cases/raw/tests 역할 분리 설명 |
| `backend/evaluation/docs/moldset_labeled_scenarios.md` | `moldset_labeled.csv` 기반 사람용 시나리오 문서 |
| `backend/evaluation/docs/workflow-branch-test-strategy.md` | workflow branch 기준 문서 |
| `backend/tests/evaluation/helpers/eval_cases.py` | 여러 case 파일을 `case_id` 기준으로 병합 |
| `backend/tests/evaluation/helpers/eval_metrics.py` | route accuracy, column F1, answerability, hallucination 등 metric helper |
| `backend/tests/evaluation/helpers/moldset_labeled_expected_answers.py` | raw CSV에서 기대 정답 계산 |
| `backend/tests/evaluation/helpers/runtime_assertions.py` | runtime/live 결과 assertion helper |
| `backend/tests/evaluation/contracts/test_dataset_contract.py` | raw dataset 행/열/라벨/스케일링 contract 검증 |
| `backend/tests/evaluation/contracts/test_project_benchmark_cases.py` | benchmark case coverage 검증 |
| `backend/tests/evaluation/runtime/test_moldset_labeled_runtime_answers.py` | LLM 없이 분석 실행 결과가 raw 정답과 맞는지 검증 |
| `backend/tests/evaluation/live/test_moldset_labeled_live_workflow_answers.py` | `RUN_LIVE_AGENT_BENCHMARK=1`일 때 live workflow 검증 |
| `backend/tests/workflow/test_moldset_workflow_branch_contracts.py` | workflow branch contract 검증 |

중요한 해석: 현재 `backend/evaluation/cases/*.jsonl`은 확장자가 jsonl이지만 한 줄 JSONL이 아니라 연속 JSON object를 decoder로 읽는 구조다. 따라서 새 case를 추가할 때도 `eval_cases.py`의 현재 loader 계약에 맞춰야 한다.

## 5. 시나리오 데이터로 활용하는 기준

시나리오는 “사용자 질문 + 선택 dataset + 기대 route + 기대 evidence + 기대 output” 묶음으로 정의한다.

### 5.1 공통 case schema 제안

```json
{
  "case_id": "moldset_label_distribution_001",
  "dataset": "moldset_labeled.csv",
  "question": "PassOrFail 라벨 분포를 알려줘.",
  "expected_route": "analysis",
  "expected_answer_status": "answerable",
  "expected_used_columns": ["PassOrFail"],
  "expected_evidence_keys": ["source_id", "used_columns", "analysis_metrics"],
  "expected_metrics": {
    "total_count": 2607,
    "normal_count": 2555,
    "defect_count": 52,
    "defect_rate_pct": 1.9946298427311087
  },
  "forbidden_answer_terms": ["정확도", "F1", "모델 성능"]
}
```

추가로 성능 평가용 case에는 아래 필드를 붙일 수 있다.

```json
{
  "performance_group": "small_labeled_analysis",
  "expected_max_latency_ms": 15000,
  "latency_budget_stage": {
    "planner": 5000,
    "analysis": 8000,
    "final_answer": 5000
  },
  "exclude_approval_wait_from_latency": true
}
```

### 5.2 dataset별 추천 scenario

| 우선순위 | dataset | 추천 질문 | 기대 route | 주 지표 |
|---|---|---|---|---|
| P0 | `moldset_labeled.csv` | `PassOrFail 라벨 분포를 알려줘.` | analysis | numeric consistency, column F1, evidence coverage |
| P0 | `moldset_labeled.csv` | `제품별 불량률을 계산해줘.` | analysis | table accuracy, column F1, hallucination rate |
| P0 | `moldset_labeled.csv` | `불량 사유별 건수를 알려줘.` | analysis | table accuracy, evidence coverage |
| P0 | `moldset_labeled.csv` | `숫자형 공정 컬럼들을 표준화해줘. 라벨과 제품명, 시간 컬럼은 제외해줘.` | preprocess | route accuracy, scaling target precision/recall, protected violation |
| P1 | `unlabeled_data.csv` | `이 데이터의 불량률을 계산해줘.` | analysis + abstain | answerability accuracy, forbidden term violation |
| P1 | `moldset_labeled_cn7.csv` | `이 데이터는 이미 스케일링되어 있는지 확인해줘.` | analysis | scaled detection accuracy, evidence coverage |
| P1 | `moldset_labeled_rg3.csv` | `이 데이터는 이미 스케일링되어 있는지 확인해줘.` | analysis | scaled detection accuracy |
| P1 | `labeled_data.csv` | `PassOrFail 라벨 분포를 알려줘.` | analysis | 라벨 표현 정규화, numeric consistency |
| P2 | `moldset_labeled_cn7.csv` + `moldset_labeled_rg3.csv` | `CN7과 RG3의 불량률을 비교해줘.` | analysis | multi-dataset 확장 가능성. 현재 단일 source 중심이라 미래 과제 |
| P2 | `unlabeled_data.csv` | `공정 컬럼들의 기본 통계를 요약해줘.` | analysis | 대용량 latency, rows/sec, execution success |
| P2 | `moldset_unlabeled_cn7.csv` | `이미 표준화된 데이터인지 알려줘.` | analysis | scaled detection + 대용량 성능 |
| P3 | `moldset_labeled.csv` | `제품별 불량률을 막대그래프로 보여줘.` | visualization | visualization route, chart artifact success |
| P3 | `moldset_labeled.csv` | `불량률 분석 결과를 리포트로 작성해줘.` | report | report artifact success, approval/resume success |

## 6. 정확도 계열 지표

이 프로젝트의 정확도는 “모델이 불량을 예측했는가?”보다 “Agent가 질문을 올바른 workflow로 보내고, 올바른 컬럼과 raw 숫자에 grounded된 답을 했는가?”가 핵심이다.

### 6.1 Route accuracy

목적: planner/main graph가 기대 route로 보냈는지 측정한다.

공식:

```text
route_accuracy = expected_route == actual_route 인 case 수 / 전체 case 수
```

활용:

- analysis 질문이 preprocess approval로 빠지면 실패.
- 표준화 요청이 analysis만 하고 끝나면 실패.
- 계산형 질문이 fallback RAG로 빠지면 실패.

그래프:

- `expected_route` vs `actual_route` confusion matrix
- route별 accuracy bar chart

### 6.2 Workflow branch accuracy

목적: route 문자열뿐 아니라 실제 subgraph 활성/비활성 여부를 측정한다.

체크 항목:

| branch | 기대값 예시 |
|---|---|
| selected dataset | `source_id` 존재, `dataset_selected` 경로 |
| clarification | benchmark 질문에서는 `needs_clarification=false` |
| preprocess | 라벨 분포/집계는 false, 표준화는 true |
| analysis | 정량 질문은 `analysis_result.execution_status=success` |
| RAG | CSV 계산 질문은 `fallback_rag` 아님 |
| visualization | 차트 요청 없으면 false, 그래프 요청 있으면 true |
| report | 리포트 요청 없으면 false, 보고서 요청 있으면 true |
| terminal | 성공 계산 질문은 `output.type="data_qa"` |

공식 예시:

```text
branch_accuracy = 기대 branch flag를 모두 만족한 case 수 / 전체 case 수
```

그래프:

- branch별 pass/fail stacked bar
- scenario별 branch checklist heatmap

### 6.3 Column grounding F1

목적: 답변/분석이 사용해야 할 컬럼만 사용했는지 측정한다.

공식:

```text
precision = |expected_used_columns ∩ actual_used_columns| / |actual_used_columns|
recall    = |expected_used_columns ∩ actual_used_columns| / |expected_used_columns|
F1        = 2 * precision * recall / (precision + recall)
```

예시:

- 라벨 분포: expected = [`PassOrFail`]
- 제품별 불량률: expected = [`PART_NAME`, `PassOrFail`]
- 불량 사유: expected = [`PassOrFail`, `Reason`]
- 표준화: protected columns를 제외하고 numeric process columns만 target이어야 함

그래프:

- case별 F1 bar chart
- 컬럼 category별 precision/recall chart

### 6.4 Numeric consistency rate

목적: raw CSV에서 계산 가능한 숫자가 실제 output/evidence와 일치하는지 측정한다.

공식:

```text
numeric_consistency_rate = expected_metrics가 actual_metrics 또는 answer/evidence 숫자에 모두 포함된 case 수 / expected_metrics가 있는 case 수
```

현재 canonical expected metrics:

| case | expected |
|---|---|
| 라벨 분포 | total 2,607, normal 2,555, defect 52, defect rate 1.9946% |
| 제품별 불량률 | CN7 LH 1.2640%, CN7 RH 2.5245%, RG3 LH 0%, RG3 RH 4.2301% |
| 불량 사유 | 가스 30, 미성형 12, 초기허용불량 10 |

그래프:

- expected vs actual grouped bar
- numeric error absolute/relative error bar
- case별 pass/fail bar

### 6.5 Table accuracy / table closeness

목적: group-by 결과 테이블이 raw CSV와 같은 row/key/value를 갖는지 측정한다.

평가 방식:

1. key columns 기준으로 expected/actual row를 정렬한다.
2. row 수와 key set이 같은지 본다.
3. numeric cell은 tolerance로 비교한다.
4. text cell은 exact 또는 normalized match로 비교한다.

공식 예시:

```text
table_row_match_rate = expected key가 actual table에 존재한 row 수 / expected row 수
numeric_cell_accuracy = 허용 오차 내 numeric cell 수 / 비교 대상 numeric cell 수
```

그래프:

- 제품별 불량률 expected vs actual grouped bar
- 불량 사유별 count pie/bar
- table cell error heatmap

### 6.6 Evidence coverage rate

목적: 최종 output이 필요한 evidence key를 포함하는지 측정한다.

공식:

```text
evidence_coverage_rate = expected_evidence_keys가 actual_evidence_package에 모두 존재한 case 수 / 전체 case 수
```

필수 evidence 예시:

| 질문 | expected evidence |
|---|---|
| 라벨 분포 | `source_id`, `used_columns`, `analysis_metrics` |
| 제품별 불량률 | `source_id`, `used_columns`, `analysis_table` |
| unanswerable | `source_id`, `warnings` |

그래프:

- evidence key별 coverage bar
- scenario x evidence key heatmap

### 6.7 Answerability accuracy

목적: 답변 가능한 질문과 불가능한 질문을 구분하는지 측정한다.

공식:

```text
answerability_accuracy = expected_answer_status == actual_answer_status 인 case 수 / 전체 case 수
```

핵심 negative case:

- `unlabeled_data.csv`에서 `이 데이터의 불량률을 계산해줘.`
- 기대: `PassOrFail`이 없으므로 unanswerable 또는 limited.
- 실패: 불량률 숫자를 지어내거나 “정확도/F1/모델 성능”처럼 근거 없는 성능 표현을 함.

그래프:

- answerable/unanswerable confusion matrix
- abstention success rate bar

### 6.8 Hallucinated metric rate

목적: raw/evidence에 없는 숫자나 성능 지표를 답변이 새로 만들어내는지 측정한다.

공식:

```text
hallucinated_metric_rate = 허용 숫자(expected_metrics ∪ evidence_numbers) 밖의 숫자를 답변한 case 수 / 전체 case 수
```

주의:

- 문장 속 연도나 파일명 숫자는 whitelist/ignore rule이 필요할 수 있다.
- “정확도 95%” 같은 표현은 raw 데이터에서 계산한 값이 아니면 실패다.

그래프:

- hallucination rate trend line
- case별 hallucinated number count

### 6.9 Forbidden term violation rate

목적: 단순 데이터 분석 질문에서 ML 성능으로 오해되는 표현을 막는다.

공식:

```text
forbidden_term_violation_rate = forbidden_answer_terms 중 하나라도 포함한 case 수 / 전체 case 수
```

현재 금지 표현 예시:

- `정확도`
- `F1`
- `모델 성능`
- negative case에서는 `불량률은` 같은 단정 표현도 금지 가능

그래프:

- term별 violation count
- model/prompt version별 violation trend

## 7. 전처리/데이터 품질 계열 지표

### 7.1 Scaling detection accuracy

목적: 이미 scaled-like인 데이터와 raw-scale 데이터를 구분하는지 측정한다.

기준:

```text
대표 numeric columns의 평균이 0에 가깝고 표준편차가 1에 가까우면 scaled-like
```

현재 contract 예시:

| dataset | expected |
|---|---|
| `moldset_labeled.csv` | scaled-like 아님 |
| `labeled_data.csv` | scaled-like 아님 |
| `supervised_label_cn7.csv` | scaled-like 아님 |
| `moldset_labeled_cn7.csv` | scaled-like |
| `moldset_labeled_rg3.csv` | scaled-like |
| `moldset_unlabeled_cn7.csv` | scaled-like |
| `moldset_unlabeled_rg3.csv` | scaled-like |
| `unlabeled_data.csv` | scaled-like 아님 |

공식:

```text
scaling_detection_accuracy = expected_scaled_like == actual_scaled_like 인 dataset 수 / 평가 dataset 수
```

그래프:

- dataset별 mean/std scatter
- scaled-like decision confusion matrix

### 7.2 Scaling target precision/recall

목적: 표준화 요청에서 변환해야 할 공정 numeric 컬럼만 골랐는지 측정한다.

공식:

```text
precision = |expected_scaling_target_columns ∩ actual_scaling_target_columns| / |actual_scaling_target_columns|
recall    = |expected_scaling_target_columns ∩ actual_scaling_target_columns| / |expected_scaling_target_columns|
```

`moldset_labeled.csv` 표준화 case에서 기대 target은 36개 공정 numeric 컬럼이다. `PassOrFail`, `Reason`, `PART_NAME`, `EQUIP_NAME`, `TimeStamp`는 보호 대상이다.

그래프:

- target precision/recall bar
- missing target columns table
- extra target columns table

### 7.3 Protected column violation rate

목적: 라벨, 식별자, 시간, 제품명 같은 보호 컬럼을 변형하지 않는지 측정한다.

공식:

```text
protected_column_violation_rate = changed_protected_columns가 있는 case 수 / 전체 preprocess case 수
```

실패 예시:

- `PassOrFail`을 표준화함
- `TimeStamp`를 숫자로 변환해 원본 의미를 잃음
- `PART_NAME`을 인코딩하고 원본을 덮어씀

그래프:

- protected column별 violation count
- preprocess method별 violation rate

### 7.4 Dataset contract pass rate

목적: raw dataset 자체가 benchmark 기준과 맞는지 확인한다.

공식:

```text
dataset_contract_pass_rate = row/column/required column/label contract를 통과한 dataset 수 / 전체 dataset 수
```

이 지표는 모델 성능이 아니라 benchmark 입력 신뢰도 지표다. raw 파일이 바뀌면 가장 먼저 깨져야 한다.

그래프:

- dataset별 contract pass/fail matrix
- row count/column count inventory table

## 8. 속도/성능 계열 지표

속도 개선은 한 번 실행 시간만으로 판단하면 안 된다. 같은 scenario를 여러 번 반복하고 p50/p95, stage별 latency, baseline 대비 개선율을 함께 봐야 한다.

### 8.1 End-to-end latency

목적: 사용자가 질문을 보낸 시점부터 최종 `done` event까지 걸린 시간을 측정한다.

공식:

```text
end_to_end_latency_ms = done_ts - ingress_ts
```

주의:

- approval 대기 시간이 있는 case는 사용자가 기다린 시간과 시스템 실행 시간이 섞인다.
- preprocess/report approval case는 `approval_wait_ms`를 분리하고, 시스템 latency는 approval wait을 제외한 값으로 봐야 한다.

그래프:

- scenario별 p50/p95 latency bar
- 실행 날짜별 latency trend line

### 8.2 Time to first event / first chunk

목적: 사용자가 체감하는 초기 반응 속도를 측정한다.

공식:

```text
time_to_first_thought_ms = first_thought_ts - ingress_ts
time_to_first_chunk_ms   = first_chunk_ts - ingress_ts
```

활용:

- planner가 느린지, analysis는 느리지만 진행 상태는 빨리 보여주는지 구분 가능.
- UX 관점에서는 전체 latency보다 이 지표가 더 중요할 수 있다.

그래프:

- first thought/chunk latency grouped bar
- p95 first event latency trend

### 8.3 Stage latency

목적: 전체 느림의 원인이 planner, preprocess, analysis, visualization, report 중 어디인지 파악한다.

기준 이벤트:

- `storage/logs/agent-trace.jsonl`의 `chat/*`, `workflow/snapshot`, `workflow/node_result`, `workflow/workflow_final_state`
- `storage/logs/traces/<trace_id>.json`의 step summary

공식 예시:

```text
stage_latency_ms[stage] = 다음 stage 첫 이벤트 ts - 현재 stage 첫 이벤트 ts
node_result_latency_ms[node] = node_result_ts - 이전 node_result_ts
```

더 정확한 지표를 원하면 각 node 시작/끝 이벤트를 명시적으로 로깅하도록 확장해야 한다. 현재 구조에서는 snapshot/node_result 간 시간 차이를 근사치로 쓸 수 있다.

그래프:

- stage latency stacked bar
- node별 p95 latency horizontal bar
- slowest stage Pareto chart

### 8.4 Rows per second / data-size scalability

목적: 데이터 크기가 커질 때 분석 시간이 어떻게 증가하는지 측정한다.

공식:

```text
rows_per_second = dataset_row_count / analysis_stage_latency_seconds
latency_per_1k_rows_ms = analysis_stage_latency_ms / (row_count / 1000)
```

추천 비교:

| small/medium/large | dataset | 행 |
|---|---|---:|
| small | `moldset_labeled_rg3.csv` | 1,182 |
| small | `moldset_labeled_cn7.csv` | 1,211 |
| small/medium | `moldset_labeled.csv` | 2,607 |
| medium | `supervised_label_cn7.csv` | 6,736 |
| medium | `labeled_data.csv` | 7,996 |
| large | `moldset_unlabeled_cn7.csv` | 35,239 |
| large | `moldset_unlabeled_rg3.csv` | 35,941 |
| xlarge | `unlabeled_data.csv` | 795,315 |

그래프:

- row count vs latency scatter
- row count vs rows/sec line
- dataset size bucket별 p50/p95 bar

### 8.5 Baseline 대비 속도 개선율

목적: 성능 개선 작업 전후를 숫자로 표현한다.

공식:

```text
speed_improvement_pct = (baseline_latency_ms - current_latency_ms) / baseline_latency_ms * 100
speedup_factor = baseline_latency_ms / current_latency_ms
```

예시 표현:

```text
moldset_labeled.csv 라벨 분포 scenario의 p50 end-to-end latency가 12.0s에서 8.4s로 감소했다면:
speed_improvement_pct = (12000 - 8400) / 12000 * 100 = 30%
speedup_factor = 12000 / 8400 = 1.43x
```

그래프:

- baseline vs current grouped bar
- speed improvement percentage bar
- scenario별 speedup factor chart

### 8.6 Reliability/flake 지표

속도와 함께 봐야 하는 안정성 지표다. 빠르지만 실패가 많으면 개선으로 볼 수 없다.

| 지표 | 공식 |
|---|---|
| execution success rate | `success case 수 / 전체 실행 수` |
| timeout rate | `timeout case 수 / 전체 실행 수` |
| retry count 평균 | `sum(retry_count) / 전체 실행 수` |
| error stage distribution | `error_stage`별 실패 건수 |
| approval resume success rate | `resume 후 done까지 도달한 수 / approval_required 수` |

그래프:

- error stage stacked bar
- success/timeout trend line
- retry count histogram

## 9. 그래프로 표현할 대시보드 구성

### 9.1 최소 대시보드

처음에는 아래 6개 그래프만 만들어도 충분하다.

1. **Scenario pass rate**: 전체 case 중 성공 비율.
2. **Route confusion matrix**: expected route와 actual route 비교.
3. **Metric accuracy bar**: route accuracy, column F1, numeric consistency, evidence coverage, answerability accuracy.
4. **Hallucination/forbidden term rate**: 낮을수록 좋음.
5. **Stage latency stacked bar**: planner/analysis/final answer 등 stage별 시간.
6. **Rows vs latency scatter**: 데이터 크기 증가에 따른 분석 시간.

### 9.2 확장 대시보드

| 그래프 | 목적 | x축 | y축/색상 |
|---|---|---|---|
| scenario heatmap | 어떤 case가 어떤 지표에서 실패하는지 | case_id | metric pass/fail |
| expected vs actual numeric chart | 계산값 차이 | metric name | expected/actual |
| product defect rate bar | 제조 데이터 도메인 결과 시각화 | PART_NAME | defect_rate_pct |
| defect reason pie/bar | 불량 원인 분포 | Reason | defect_count/share |
| latency trend | 성능 회귀 감지 | run date/commit | p50/p95 latency |
| model A/B comparison | 모델/프롬프트 비교 | model_id | metric score/latency |
| evidence key coverage | output contract 구멍 확인 | evidence key | coverage rate |

## 10. benchmark result 저장 스키마 제안

향후 runner가 산출할 result 파일은 `backend/evaluation/results/` 같은 별도 폴더에 저장하는 것이 좋다. raw/cases/docs와 결과물을 분리해야 재실행과 비교가 쉽다.

### 10.1 case-level result JSONL

```json
{
  "run_id": "bench-2026-05-18-001",
  "commit": "<git commit>",
  "case_id": "moldset_label_distribution_001",
  "dataset": "moldset_labeled.csv",
  "question": "PassOrFail 라벨 분포를 알려줘.",
  "model_id": "gpt-5-nano",
  "expected_route": "analysis",
  "actual_route": "analysis",
  "expected_used_columns": ["PassOrFail"],
  "actual_used_columns": ["PassOrFail"],
  "expected_answer_status": "answerable",
  "actual_answer_status": "answerable",
  "expected_metrics": {
    "total_count": 2607,
    "normal_count": 2555,
    "defect_count": 52,
    "defect_rate_pct": 1.9946298427311087
  },
  "actual_metrics": {
    "total_count": 2607,
    "normal_count": 2555,
    "defect_count": 52,
    "defect_rate_pct": 1.9946298427311087
  },
  "actual_evidence_package": {
    "source_id": "moldset_labeled.csv",
    "used_columns": ["PassOrFail"],
    "analysis_metrics": {}
  },
  "latency_ms": {
    "end_to_end": 8400,
    "planner": 2100,
    "analysis": 4200,
    "final_answer": 1600
  },
  "trace_id": "...",
  "status": "success"
}
```

### 10.2 aggregate metrics JSON

```json
{
  "run_id": "bench-2026-05-18-001",
  "case_count": 12,
  "route_accuracy": 0.9167,
  "mean_column_grounding_f1": 0.94,
  "numeric_consistency_rate": 0.875,
  "answerability_accuracy": 1.0,
  "evidence_coverage_rate": 0.8333,
  "hallucinated_metric_rate": 0.0833,
  "forbidden_term_violation_rate": 0.0,
  "execution_success_rate": 0.9167,
  "latency_p50_ms": 8400,
  "latency_p95_ms": 22100
}
```

## 11. 실행 단계 제안

### 11.1 1단계: 현재 deterministic benchmark 고정

목표: raw dataset과 expected answer가 변하지 않았는지 항상 확인한다.

권장 명령:

```bash
PYTHONPATH=. pytest -q \
  backend/tests/evaluation/contracts \
  backend/tests/evaluation/metrics \
  backend/tests/evaluation/runtime
```

확인 지표:

- dataset contract pass rate
- metric helper unit test pass
- runtime raw metric consistency

### 11.2 2단계: live benchmark gate

목표: 실제 LangGraph + LLM workflow가 canonical case를 통과하는지 확인한다.

권장 명령:

```bash
RUN_LIVE_AGENT_BENCHMARK=1 PYTHONPATH=. pytest -q backend/tests/evaluation/live
```

주의:

- API key/model 환경에 의존하므로 기본 CI에서는 skip하는 것이 맞다.
- live 결과는 반복 실행 변동이 있으므로 exact prose match가 아니라 숫자/컬럼/evidence 중심으로 평가해야 한다.

### 11.3 3단계: result collector 추가

목표: pytest assertion만 남기지 말고 case별 result JSONL/CSV를 남긴다.

수집 항목:

- case metadata: `case_id`, `dataset`, `question`, expected fields
- actual route/state: `planning_result`, `handoff`, terminal output type
- actual evidence: `evidence_package`, `analysis_result.raw_metrics`, `analysis_result.table`
- text answer: 최종 `output.content`
- trace IDs: `trace_id`, `session_id`, `run_id`
- timestamps: ingress, first thought, node_result, done
- latency breakdown
- metric scores

### 11.4 4단계: graph report 생성

목표: benchmark 결과를 사람이 볼 수 있는 그래프로 저장한다.

추천 산출물:

```text
backend/evaluation/results/
├── runs/
│   └── bench-2026-05-18-001.jsonl
├── aggregate/
│   └── bench-2026-05-18-001.metrics.json
└── reports/
    ├── bench-2026-05-18-001.md
    ├── route_confusion_matrix.png
    ├── metric_scores.png
    ├── stage_latency_stacked.png
    └── rows_vs_latency.png
```

## 12. 현재 cases 확장 제안

현재 canonical case는 `moldset_labeled.csv` 중심이다. raw 폴더 전체를 활용하려면 아래 case를 추가하면 좋다.

### 12.1 `labeled_data.csv` 라벨 표현 정규화

목적: `Y/N` 라벨을 `0/1`과 다르게 처리해야 하는 데이터셋도 correctly grounded되는지 평가한다.

추천 case:

```json
{
  "case_id": "labeled_data_label_distribution_001",
  "dataset": "labeled_data.csv",
  "question": "PassOrFail 라벨 분포를 알려줘.",
  "expected_route": "analysis",
  "expected_answer_status": "answerable",
  "expected_used_columns": ["PassOrFail"],
  "expected_metrics": {
    "total_count": 7996,
    "normal_count": 7925,
    "defect_count": 71,
    "defect_rate_pct": 0.887943971985993
  },
  "label_mapping": {"Y": "normal", "N": "defect"}
}
```

### 12.2 CN7/RG3 scaled detection

목적: 이미 표준화된 파일에서 불필요한 preprocess를 추천하지 않는지 평가한다.

추천 case:

```json
{
  "case_id": "rg3_scaled_detection_001",
  "dataset": "moldset_labeled_rg3.csv",
  "question": "이 데이터는 이미 스케일링되어 있는지 확인해줘.",
  "expected_route": "analysis",
  "expected_answer_status": "answerable",
  "expected_judgement": "already_scaled_like",
  "expected_used_columns": ["Injection_Time", "Filling_Time", "Plasticizing_Time", "Cycle_Time"],
  "expected_evidence_keys": ["source_id", "used_columns", "analysis_metrics"]
}
```

### 12.3 unlabeled negative answerability

목적: 라벨 없는 데이터에서 불량률/정확도/F1을 지어내지 않는지 평가한다.

추천 case:

```json
{
  "case_id": "moldset_unlabeled_cn7_defect_rate_unanswerable_001",
  "dataset": "moldset_unlabeled_cn7.csv",
  "question": "이 데이터의 불량률을 계산해줘.",
  "expected_route": "analysis",
  "expected_answer_status": "unanswerable",
  "expected_used_columns": [],
  "expected_evidence_keys": ["source_id", "warnings"],
  "expected_reason": "PassOrFail 같은 정답 라벨 컬럼이 없음",
  "forbidden_answer_terms": ["정확도", "F1", "모델 성능은", "불량률은"]
}
```

### 12.4 large dataset performance

목적: 대용량 CSV에서 분석 latency와 rows/sec를 측정한다.

추천 case:

```json
{
  "case_id": "unlabeled_data_basic_profile_latency_001",
  "dataset": "unlabeled_data.csv",
  "question": "공정 컬럼들의 기본 통계를 요약해줘.",
  "expected_route": "analysis",
  "expected_answer_status": "answerable",
  "expected_used_columns": ["Injection_Time", "Filling_Time", "Cycle_Time"],
  "performance_group": "xlarge_raw_analysis",
  "latency_metric_targets": ["end_to_end_latency_ms", "analysis_latency_ms", "rows_per_second"]
}
```

## 13. 해석상 주의사항

1. raw dataset의 `PassOrFail`이 있다고 해서 곧바로 ML classifier 정확도를 평가할 수 있는 것은 아니다. 현재 프로젝트는 분석 agent이므로, 우선은 답변/route/evidence 정확도를 평가해야 한다.
2. ML 모델 성능을 평가하려면 별도 train/test split, feature leakage 방지, classifier baseline, class imbalance 처리, precision/recall/F1 정의가 추가로 필요하다.
3. `moldset_labeled.csv`는 불량 52건, 정상 2,555건으로 매우 불균형하다. 단순 accuracy는 항상 정상이라고 예측해도 약 98%가 되므로 ML 성능 지표로 부적절하다.
4. unlabeled 파일에서 불량률을 계산하려는 답변은 실패해야 한다. 라벨이 없는 데이터는 “계산 불가”를 올바르게 말하는 능력을 보는 negative case다.
5. 속도 개선 수치는 반드시 baseline run과 current run의 동일 case, 동일 모델, 동일 환경 반복 측정으로 비교해야 한다.
6. trace 기반 stage latency는 현재 이벤트 간 시간 차이로 근사할 수 있으나, node start/end 이벤트가 없으면 완전한 측정은 아니다. 성능 최적화용으로 쓰려면 node timer를 명시적으로 추가하는 것이 좋다.
7. raw 파일은 local artifact로 취급된다. CI나 다른 환경에서는 파일이 없을 수 있으므로 skip gate와 dataset availability check가 필요하다.

## 14. 권장 우선순위

| 우선순위 | 작업 | 기대 효과 |
|---|---|---|
| P0 | `moldset_labeled.csv` canonical analysis/preprocess/live benchmark 유지 | 현재 프로젝트 핵심 workflow 품질을 안정적으로 수치화 |
| P0 | case별 result JSONL 저장 | 정확도/근거/latency 그래프 생성 가능 |
| P1 | `labeled_data.csv`, `moldset_labeled_rg3.csv`, unlabeled moldset case 추가 | raw 폴더 전체 활용도 증가, 라벨/스케일링/negative coverage 확대 |
| P1 | trace timestamp 기반 latency collector 추가 | 속도 개선 수치를 p50/p95/stage별로 표현 가능 |
| P2 | benchmark report markdown + PNG 자동 생성 | 발표/문서/개선 전후 비교에 바로 사용 가능 |
| P2 | model/prompt A/B 비교 필드 추가 | 모델 선택과 prompt 변경 효과를 정량 비교 |
| P3 | multi-dataset comparison scenario | 단일 source 중심 아키텍처를 넘는 확장 평가 |

## 15. 최종 metric set 제안

최소한 아래 지표를 aggregate report에 포함하는 것을 권장한다.

| 그룹 | 지표 | 방향 | 설명 |
|---|---|---|---|
| Routing | `route_accuracy` | 높을수록 좋음 | 기대 route와 실제 route 일치율 |
| Routing | `branch_accuracy` | 높을수록 좋음 | preprocess/analysis/RAG/visualization/report 활성 조건 일치율 |
| Grounding | `mean_column_grounding_f1` | 높을수록 좋음 | 사용 컬럼 grounding 품질 |
| Grounding | `evidence_coverage_rate` | 높을수록 좋음 | 필요한 evidence key 포함율 |
| Numeric | `numeric_consistency_rate` | 높을수록 좋음 | raw CSV 계산값과 output 숫자 일치율 |
| Numeric | `table_cell_accuracy` | 높을수록 좋음 | group-by table cell 일치율 |
| Safety | `answerability_accuracy` | 높을수록 좋음 | answerable/unanswerable 구분 정확도 |
| Safety | `hallucinated_metric_rate` | 낮을수록 좋음 | 근거 없는 숫자 생성률 |
| Safety | `forbidden_term_violation_rate` | 낮을수록 좋음 | 금지 성능 표현 위반률 |
| Preprocess | `scaling_target_precision` | 높을수록 좋음 | 변환 대상 컬럼 precision |
| Preprocess | `scaling_target_recall` | 높을수록 좋음 | 변환 대상 컬럼 recall |
| Preprocess | `protected_column_violation_rate` | 낮을수록 좋음 | 보호 컬럼 변형률 |
| Runtime | `execution_success_rate` | 높을수록 좋음 | workflow 성공률 |
| Runtime | `timeout_rate` | 낮을수록 좋음 | timeout 비율 |
| Speed | `end_to_end_latency_p50_ms` | 낮을수록 좋음 | 전체 실행 p50 |
| Speed | `end_to_end_latency_p95_ms` | 낮을수록 좋음 | 전체 실행 p95 |
| Speed | `stage_latency_p95_ms` | 낮을수록 좋음 | stage별 p95 |
| Speed | `rows_per_second` | 높을수록 좋음 | 데이터 크기 대비 처리량 |
| Speed | `speed_improvement_pct` | 높을수록 좋음 | baseline 대비 개선율 |

## 16. 산출물 판정 기준

이 raw 데이터셋 활용이 “우리 프로젝트 기준의 평가 지표”로 자리 잡으려면 아래가 충족되어야 한다.

1. 모든 benchmark case가 `backend/evaluation/cases/`에 machine-readable 형태로 정의된다.
2. raw dataset contract가 `backend/tests/evaluation/contracts/`에서 검증된다.
3. expected answer는 raw CSV에서 계산되는 helper를 통해 생성되거나 검증된다.
4. live/runtime 실행 결과가 case-level result로 저장된다.
5. aggregate metrics JSON이 생성된다.
6. 최소 대시보드 그래프가 생성된다.
7. 문서에는 “현재 측정된 결과”와 “향후 측정 계획”이 분리되어 표시된다.

현재 repository는 1~3의 상당 부분과 일부 runtime/live 검증 기반을 이미 갖추고 있다. 다음 핵심 작업은 **case-level result 저장 + trace 기반 latency 수집 + graph/report 생성**이다.
