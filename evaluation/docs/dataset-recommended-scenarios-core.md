# Dataset별 추천 시나리오 핵심 요약

작성일: 2026-05-18  
원본: `evaluation/docs/raw-dataset-metric-utilization-analysis.md`의 `5.2 dataset별 추천 scenario`

## 핵심 결론

`raw-dataset-metric-utilization-analysis.md`에서 실제로 테스트·데모·벤치마크로 가져가야 할 중심은 **5.2의 dataset별 추천 scenario**다. 이 표는 raw 제조 데이터셋을 프로젝트 평가용 scenario oracle로 바꾸기 위한 우선순위, 질문, 기대 route, 평가 지표를 한 번에 정의한다.

현재 프로젝트에서 P0/P1 benchmark는 단순히 `expected_route`만 확인하면 부족하다. 아래 계약까지 단계적으로 검증해야 한다.

1. **dataset contract**: raw CSV 자체가 기대 행 수, 컬럼, 라벨 분포, 스케일링 성격을 유지하는가?
2. **route/branch contract**: planner/main workflow가 기대 branch로 들어가는가?
3. **used column grounding**: 답변·분석·evidence가 기대 컬럼에 grounded되어 있는가?
4. **metric/table oracle**: raw CSV에서 직접 계산한 숫자·표와 runtime 결과가 일치하는가?
5. **evidence contract**: `source_id`, `used_columns`, `analysis_metrics`, `analysis_table`, `answer_quality`가 최종 payload에 보존되는가?
6. **final answer quality**: 최종 문장이 근거 숫자를 포함하고, 계산 불가능한 경우에는 abstain하며, 금지 표현/환각 지표를 만들지 않는가?
7. **preprocess approval/protection**: 전처리 요청은 approval로 멈추고 보호 컬럼을 제외하는가?

나머지 장은 5.2를 보조한다.

- 3장: 각 dataset을 왜 쓰는지에 대한 근거
- 5.1: scenario를 case 파일로 옮길 때 필요한 공통 schema
- 6~7장: scenario 결과를 어떤 지표로 점수화할지에 대한 측정 체계
- 14장: 실제 반영 순서에 대한 운영 우선순위

## 현재 프로젝트에서 우선 테스트해야 할 것

현재 repo에는 `backend/tests/test_chat_sse_contract.py`, `backend/tests/test_orchestration_evidence_contract.py`처럼 SSE/evidence 계약 테스트는 있지만, `evaluation/raw/*.csv`를 oracle로 삼아 P0/P1 질문을 end-to-end benchmark case로 고정하는 테스트 계층은 별도로 설계해야 한다. 새 최상위 `tests/` 디렉터리는 만들지 않고, pytest 코드는 `backend/tests/evaluation/` 아래에 둔다.

권장 테스트 계층은 아래 순서다.

| 계층 | 목적 | 실패 시 의미 | 기본 실행 여부 |
|---|---|---|---|
| Dataset contract | raw CSV 행 수·컬럼·라벨·스케일링 oracle 고정 | 데이터 파일이 바뀌었거나 benchmark 전제가 깨짐 | 항상 실행 |
| Case contract | `evaluation/cases/*.jsonl` schema와 coverage 검증 | benchmark 정의 누락/오타 | 항상 실행 |
| Runtime deterministic | LLM 없이 분석/전처리 core가 oracle과 일치하는지 검증 | 코드 실행·집계·전처리 계약 실패 | 항상 실행 |
| Workflow branch | fake/minimal service로 planner route, evidence, node result, approval contract 검증 | orchestration 연결 실패 | 항상 실행 |
| Live benchmark | 실제 LangGraph + LLM + raw dataset으로 최종 답변 검증 | 모델/프롬프트/통합 runtime 품질 저하 | `RUN_LIVE_AGENT_BENCHMARK=1`일 때만 실행 |

## P0 상세 설계 — 즉시 benchmark로 고정할 canonical scenario

P0는 `moldset_labeled.csv`를 기준으로 현재 제품의 핵심 workflow 품질을 가장 안정적으로 검증하는 묶음이다. P0 pass 기준은 `route`만이 아니라 **route + used columns + raw metric/table + evidence + final answer + preprocess approval/protection**이다.

### P0 공통 dataset oracle

대상 파일: `evaluation/raw/moldset_labeled.csv`

| 항목 | 기대값 |
|---|---:|
| 총 행 수 | 2,607 |
| 총 컬럼 수 | 47 |
| `PassOrFail=0` 정상 | 2,555 |
| `PassOrFail=1` 불량 | 52 |
| 불량률 | 1.9946298427311087% |
| 필수 컬럼 | `PassOrFail`, `PART_NAME`, `Reason`, `TimeStamp`, `PART_FACT_SERIAL`, `PART_NO` |

제품별 oracle:

| PART_NAME | total_count | defect_count | defect_rate_pct |
|---|---:|---:|---:|
| `CN7 W/S SIDE MLD'G LH` | 712 | 9 | 1.2640449438202246 |
| `CN7 W/S SIDE MLD'G RH` | 713 | 18 | 2.524544179523142 |
| `RG3 MOLD'G W/SHLD, LH` | 591 | 0 | 0.0 |
| `RG3 MOLD'G W/SHLD, RH` | 591 | 25 | 4.230118443316413 |

불량 사유별 oracle은 `PassOrFail=1`만 대상으로 계산한다.

| Reason | defect_count |
|---|---:|
| `가스` | 30 |
| `미성형` | 12 |
| `초기허용불량` | 10 |

### P0-A. 라벨 분포 분석

| 항목 | 설계 |
|---|---|
| dataset | `moldset_labeled.csv` |
| 질문 | `PassOrFail 라벨 분포를 알려줘.` |
| 기대 route | `analysis` |
| 기대 used columns | `PassOrFail` |
| 기대 output type | `data_qa` |
| 핵심 목적 | 단일 컬럼 count/rate가 raw CSV oracle과 일치하는지 검증 |

검증해야 할 것:

1. **Route/branch**
   - `planning_result.route` 또는 handoff의 다음 단계가 `analysis`여야 한다.
   - `preprocess`, `rag`, `visualization`, `report`로 빠지면 실패다.
2. **Used columns**
   - `analysis_result.used_columns`, `evidence_package.used_columns`, `node_results` 중 최소 하나 이상에서 `PassOrFail`이 확인되어야 한다.
   - 허용 범위: 정확히 `PassOrFail`만 쓰는 것이 최선이다. 불필요 컬럼이 섞이면 column precision 저하로 기록한다.
3. **Metric oracle**
   - `total_count=2607`, `normal_count=2555`, `defect_count=52`.
   - `defect_rate_pct`는 `52 / 2607 * 100`과 tolerance 내에서 일치해야 한다.
   - 허용 tolerance: count는 exact match, rate는 `abs(actual - expected) <= 1e-6` 또는 출력 문자열 검증에서는 반올림 허용.
4. **Evidence contract**
   - `evidence_package.source_id`가 선택 dataset을 가리켜야 한다.
   - `evidence_package.analysis_metrics`에 라벨 분포 숫자가 있어야 한다.
   - `answer_quality.status`는 `answerable`이어야 한다.
5. **Final answer quality**
   - 최종 답변에 `2607`, `2555`, `52`, `1.99` 또는 동등한 반올림 표현이 포함되어야 한다.
   - `정확도`, `F1`, `모델 성능`, `예측 성능`처럼 분류 모델 성능으로 오해시키는 표현은 금지한다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| route accuracy | `actual_route == analysis` |
| column grounding F1 | expected `{"PassOrFail"}` vs actual used columns |
| numeric consistency | expected metrics와 actual metrics exact/float-close 비교 |
| evidence coverage | `source_id`, `used_columns`, `analysis_metrics` 존재 여부 |
| forbidden term violation rate | 금지 표현이 하나라도 있으면 fail |

### P0-B. 제품별 불량률 분석

| 항목 | 설계 |
|---|---|
| dataset | `moldset_labeled.csv` |
| 질문 | `제품별 불량률을 계산해줘.` |
| 기대 route | `analysis` |
| 기대 used columns | `PART_NAME`, `PassOrFail` |
| 기대 output type | `data_qa` |
| 핵심 목적 | group-by table 정확도와 임의 제품/수치 hallucination 방지 |

검증해야 할 것:

1. **Route/branch**
   - analysis route로 진입해야 한다.
2. **Used columns**
   - `PART_NAME`, `PassOrFail`이 모두 사용되어야 한다.
   - `Reason`만 사용하거나 `PART_NAME` 없이 전체 불량률만 답하면 실패다.
3. **Table oracle**
   - raw CSV에서 `PART_NAME`별 `total_count`, `defect_count`, `defect_rate_pct`를 계산한다.
   - runtime `analysis_result.table` 또는 `evidence_package.analysis_table`과 비교한다.
   - row key는 제품명, metric key는 count/rate alias 차이를 허용하되 값은 raw oracle과 일치해야 한다.
4. **Evidence contract**
   - `analysis_table`이 비어 있으면 실패다.
   - `analysis_metrics`만 있고 제품별 table이 없으면 table accuracy fail로 기록한다.
5. **Final answer quality**
   - 최소 4개 제품명이 모두 답변 또는 table에 나타나야 한다.
   - 없는 제품명을 만들거나 불량률 순위를 잘못 말하면 fail 또는 partial로 기록한다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| route accuracy | `actual_route == analysis` |
| column grounding F1 | expected `{"PART_NAME", "PassOrFail"}` vs actual used columns |
| table accuracy / table closeness | 제품명별 count exact, rate float-close |
| hallucinated metric rate | raw oracle에 없는 제품명/숫자 출현 비율 |
| evidence coverage | `analysis_table`, `used_columns`, `source_id` 존재 여부 |

### P0-C. 불량 사유별 건수 분석

| 항목 | 설계 |
|---|---|
| dataset | `moldset_labeled.csv` |
| 질문 | `불량 사유별 건수를 알려줘.` |
| 기대 route | `analysis` |
| 기대 used columns | `Reason`, `PassOrFail` |
| 기대 output type | `data_qa` |
| 핵심 목적 | 결함 row 필터링 후 categorical aggregation이 정확한지 검증 |

검증해야 할 것:

1. **Route/branch**
   - analysis route로 진입해야 한다.
2. **Used columns**
   - `Reason`, `PassOrFail`이 모두 사용되어야 한다.
3. **Filter contract**
   - `PassOrFail=1` 불량 row만 대상으로 `Reason`을 집계해야 한다.
   - 정상 row의 `Reason=None` 2,555건을 사유 집계에 포함하면 실패다.
4. **Table oracle**
   - `가스=30`, `미성형=12`, `초기허용불량=10`과 일치해야 한다.
5. **Evidence/final answer**
   - `analysis_table` 또는 final answer에 위 세 사유와 건수가 포함되어야 한다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| route accuracy | `actual_route == analysis` |
| column grounding F1 | expected `{"Reason", "PassOrFail"}` vs actual used columns |
| table accuracy | reason별 count exact |
| evidence coverage | `analysis_table`, `used_columns`, `source_id` 존재 여부 |
| hallucination rate | raw에 없는 사유/건수 출현 여부 |

### P0-D. 전처리 표준화 + 보호 컬럼 제외

| 항목 | 설계 |
|---|---|
| dataset | `moldset_labeled.csv` |
| 질문 | `숫자형 공정 컬럼들을 표준화해줘. 라벨과 제품명, 시간 컬럼은 제외해줘.` |
| 기대 route | `preprocess` |
| 기대 approval | `approval_required` 발생 |
| 핵심 목적 | 전처리 route, approval gate, scale target, protected column exclusion 검증 |

검증해야 할 것:

1. **Route/branch**
   - `preprocess` route로 진입해야 한다.
   - 단순 analysis로 끝나면 실패다.
2. **Approval gate**
   - 실제 적용 전 `approval_required` event가 발생해야 한다.
   - approval payload의 `stage`는 `preprocess`, `kind`는 plan review 계열이어야 한다.
3. **Scale operation**
   - `preprocess_plan.operations`에 `op=scale`이 포함되어야 한다.
   - 대상 컬럼은 숫자형 공정 컬럼이어야 한다.
4. **Protected column exclusion**
   - 아래 컬럼은 scale 대상에서 제외되어야 한다.
     - 라벨: `PassOrFail`
     - 제품/식별: `PART_NAME`, `PART_NO`, `PART_FACT_SERIAL`, `_id`
     - 시간: `TimeStamp`, `PART_FACT_PLAN_DATE`
   - 보호 컬럼이 하나라도 포함되면 `protected_column_violation` fail이다.
5. **Resume 후 결과**
   - 승인 resume 테스트에서는 `approved_plan`이 executor로 전달되고 `preprocess_result.status`가 `applied` 또는 성공 계열이어야 한다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| route accuracy | `actual_route == preprocess` |
| approval gate success | approval event 발생 여부 |
| scaling target precision | 실제 scale 대상 중 허용 숫자형 공정 컬럼 비율 |
| scaling target recall | 기대 숫자형 공정 컬럼 중 scale 대상으로 잡힌 비율 |
| protected column violation rate | 보호 컬럼이 대상에 포함되면 fail |
| resume success | approve 후 `preprocess_result.status` 성공 여부 |

## P1 상세 설계 — 품질 방어와 데이터 특성 판단 scenario

P1은 P0처럼 canonical happy path만 보는 것이 아니라, 모델이 잘못된 숫자를 만들어내지 않는지와 dataset 특성을 수치 근거로 판단하는지 확인한다.

### P1-A. 라벨 없는 데이터의 불량률 질문 abstain

| 항목 | 설계 |
|---|---|
| dataset | `unlabeled_data.csv` |
| 질문 | `이 데이터의 불량률을 계산해줘.` |
| 기대 route | `analysis + abstain` |
| 기대 answer status | `unanswerable` 또는 명시적 `limited` |
| 핵심 목적 | `PassOrFail` 없는 데이터에서 불량률을 조작하지 않는지 검증 |

Dataset oracle:

| 항목 | 기대값 |
|---|---:|
| 총 행 수 | 795,315 |
| 총 컬럼 수 | 46 |
| `PassOrFail` 컬럼 | 없음 |
| raw-scale 예시 | `Cycle_Time` 평균 약 58.030807, std 약 16.916262 |

검증해야 할 것:

1. **Dataset contract**
   - `PassOrFail` 컬럼이 없어야 한다.
2. **Route/branch**
   - 질문 성격은 analysis지만, 결과는 answerable 계산이 아니라 abstain이어야 한다.
3. **Answerability**
   - `answer_quality.status`가 `unanswerable` 또는 정책상 `limited`여야 한다.
   - 답변은 “라벨 컬럼이 없어 불량률을 계산할 수 없다”는 이유를 포함해야 한다.
4. **No fabricated metrics**
   - `defect_count`, `defect_rate_pct`, `normal_count` 같은 불량률 숫자를 만들어내면 실패다.
   - `PassOrFail`이 없는데 `0/1`, `Y/N` 분포를 말하면 실패다.
5. **Evidence contract**
   - evidence warning에 분석 근거 부족 또는 missing label 관련 사유가 들어가야 한다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| answerability accuracy | expected unanswerable/limited와 actual status 비교 |
| forbidden term violation | fabricated rate/count, 모델 성능 표현 금지 |
| hallucinated metric rate | raw에 없는 라벨 기반 숫자 생성 여부 |
| evidence coverage | missing label/insufficient evidence warning 존재 여부 |

### P1-B. CN7 scaled-like 판단

| 항목 | 설계 |
|---|---|
| dataset | `moldset_labeled_cn7.csv` |
| 질문 | `이 데이터는 이미 스케일링되어 있는지 확인해줘.` |
| 기대 route | `analysis` |
| 기대 판단 | 이미 스케일링된 데이터로 판단 |
| 핵심 목적 | 평균 0, 표준편차 1 근거로 scaled-like 판단을 하는지 검증 |

Dataset oracle:

| 항목 | 기대값 |
|---|---:|
| 총 행 수 | 1,211 |
| 총 컬럼 수 | 26 |
| `PassOrFail=0` | 1,194 |
| `PassOrFail=1` | 17 |
| `Injection_Time` mean/std | 약 0.0 / 1.000413 |
| `Filling_Time` mean/std | 약 0.0 / 1.000413 |
| `Plasticizing_Time` mean/std | 약 0.0 / 1.000413 |
| `Cycle_Time` mean/std | 약 0.0 / 1.000413 |

검증해야 할 것:

1. **Route/branch**
   - analysis route로 진입해야 한다.
2. **Used columns**
   - 최소 `Injection_Time`, `Filling_Time`, `Plasticizing_Time`, `Cycle_Time` 중 2개 이상을 근거 컬럼으로 사용해야 한다.
3. **Scaled detection**
   - 평균 절댓값이 작은 값, 표준편차가 1에 가까운 값을 근거로 “이미 스케일링됨” 또는 “표준화된 것으로 보임”이라고 판단해야 한다.
4. **Evidence/final answer**
   - 답변이나 evidence에 mean/std 근거가 포함되어야 한다.
   - 단순히 “스케일링됨”이라고만 말하고 수치 근거가 없으면 evidence coverage를 partial로 둔다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| scaled detection accuracy | expected scaled-like == actual 판단 |
| evidence coverage | mean/std 근거 포함 여부 |
| column grounding F1 | 기준 공정 컬럼 vs actual used columns |
| numeric consistency | mean/std 값이 oracle tolerance 내인지 |

### P1-C. RG3 scaled-like 판단

| 항목 | 설계 |
|---|---|
| dataset | `moldset_labeled_rg3.csv` |
| 질문 | `이 데이터는 이미 스케일링되어 있는지 확인해줘.` |
| 기대 route | `analysis` |
| 기대 판단 | 이미 스케일링된 데이터로 판단 |
| 핵심 목적 | CN7이 아닌 RG3 subset에서도 scaled-like 판단이 일관적인지 검증 |

Dataset oracle:

| 항목 | 기대값 |
|---|---:|
| 총 행 수 | 1,182 |
| 총 컬럼 수 | 26 |
| `PassOrFail=0` | 1,157 |
| `PassOrFail=1` | 25 |
| `Injection_Time` mean/std | 약 0.0 / 1.000423 |
| `Filling_Time` mean/std | 약 0.0 / 1.000423 |
| `Plasticizing_Time` mean/std | 약 0.0 / 1.000423 |
| `Cycle_Time` mean/std | 약 0.0 / 1.000423 |

검증은 P1-B와 동일하다. 단, CN7 전용 제품명/컬럼명을 답변에 섞지 않는지도 확인한다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| scaled detection accuracy | expected scaled-like == actual 판단 |
| evidence coverage | mean/std 근거 포함 여부 |
| numeric consistency | mean/std 값 float-close |
| hallucination rate | CN7 등 다른 dataset 근거가 섞였는지 여부 |

### P1-D. `Y`/`N` 라벨 표현 정규화

| 항목 | 설계 |
|---|---|
| dataset | `labeled_data.csv` |
| 질문 | `PassOrFail 라벨 분포를 알려줘.` |
| 기대 route | `analysis` |
| 기대 used columns | `PassOrFail` |
| 핵심 목적 | `0`/`1`이 아닌 `Y`/`N` 라벨 표현을 올바르게 처리하는지 검증 |

Dataset oracle:

| 항목 | 기대값 |
|---|---:|
| 총 행 수 | 7,996 |
| 총 컬럼 수 | 45 |
| `PassOrFail=Y` | 7,925 |
| `PassOrFail=N` | 71 |
| `N` 비율 | 0.8879439719859929% |

검증해야 할 것:

1. **Route/branch**
   - analysis route로 진입해야 한다.
2. **Used columns**
   - `PassOrFail`을 사용해야 한다.
3. **Label normalization**
   - 이 dataset에서는 `Y`/`N` 표현을 그대로 보고하거나, 프로젝트 정책에 따라 정상/불량으로 정규화해야 한다.
   - 단, `Y/N`을 임의로 `0/1`로 바꾸면서 의미를 반대로 해석하면 실패다.
4. **Metric oracle**
   - `total_count=7996`, `Y=7925`, `N=71`, `N rate≈0.8879439719859929%`.
5. **Final answer quality**
   - `Y`, `N` 라벨 의미가 불확실하면 “라벨 의미 확인 필요”를 명시해도 된다.
   - 확신 없이 `Y=불량`, `N=정상`처럼 의미를 뒤집어 단정하면 실패다.

지표 검증:

| 지표 | 계산/판정 |
|---|---|
| route accuracy | `actual_route == analysis` |
| label normalization accuracy | `Y/N` count와 의미 처리 일치 여부 |
| numeric consistency | count/rate oracle 비교 |
| column grounding F1 | expected `{"PassOrFail"}` vs actual used columns |
| forbidden term violation | 모델 성능/예측 정확도 표현 금지 |

## Case 파일 설계

`evaluation/cases/`를 만들고 P0/P1을 priority별로 나누는 것을 권장한다.

```text
evaluation/
├── raw/
├── docs/
└── cases/
    ├── p0_moldset_analysis_cases.jsonl
    ├── p0_moldset_preprocess_cases.jsonl
    └── p1_dataset_quality_cases.jsonl
```

각 case는 최소한 아래 필드를 가진다.

```json
{
  "case_id": "p0_moldset_label_distribution",
  "priority": "P0",
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

Table case는 `expected_table`을 추가한다.

```json
{
  "case_id": "p0_moldset_defect_rate_by_part",
  "priority": "P0",
  "dataset": "moldset_labeled.csv",
  "question": "제품별 불량률을 계산해줘.",
  "expected_route": "analysis",
  "expected_used_columns": ["PART_NAME", "PassOrFail"],
  "expected_table_key": "PART_NAME",
  "expected_table_metrics": ["total_count", "defect_count", "defect_rate_pct"]
}
```

Answerability case는 `expected_answer_status`와 금지 metric을 더 강하게 둔다.

```json
{
  "case_id": "p1_unlabeled_defect_rate_abstain",
  "priority": "P1",
  "dataset": "unlabeled_data.csv",
  "question": "이 데이터의 불량률을 계산해줘.",
  "expected_route": "analysis",
  "expected_answer_status": "unanswerable",
  "expected_missing_columns": ["PassOrFail"],
  "forbidden_metric_keys": ["defect_count", "defect_rate_pct", "normal_count"]
}
```

## 테스트 코드 설계

새 최상위 `tests/` 폴더는 만들지 않는다. 현재 프로젝트 규칙에 맞춰 pytest 코드는 `backend/tests/` 아래에 둔다.

```text
backend/tests/evaluation/
├── conftest.py
├── helpers/
│   ├── eval_cases.py
│   ├── moldset_p0_oracles.py
│   ├── p1_dataset_oracles.py
│   └── runtime_assertions.py
├── contracts/
│   ├── test_p0_moldset_dataset_contract.py
│   ├── test_p1_dataset_contracts.py
│   └── test_project_benchmark_cases.py
├── metrics/
│   └── test_eval_metrics.py
├── runtime/
│   ├── test_p0_moldset_analysis_runtime.py
│   └── test_p1_dataset_quality_runtime.py
├── workflow/
│   ├── test_p0_moldset_workflow_contracts.py
│   └── test_p1_dataset_quality_workflow_contracts.py
└── live/
    ├── conftest.py
    └── test_p0_p1_live_benchmark.py
```

### Helper 설계

`moldset_p0_oracles.py`:

- `read_rows(dataset_name: str) -> list[dict[str, str]]`
- `expected_label_distribution() -> dict`
- `expected_defect_rate_by_part() -> list[dict]`
- `expected_defect_reason_counts() -> list[dict]`
- `assert_float_close(actual, expected, tolerance=1e-6)`
- `assert_table_close(actual_table, expected_table, key_columns, metric_columns)`

`p1_dataset_oracles.py`:

- `dataset_shape(dataset_name) -> dict`
- `label_counts(dataset_name) -> dict`
- `numeric_mean_std(dataset_name, columns) -> dict`
- `is_scaled_like(mean_std, mean_abs_max=0.05, std_min=0.95, std_max=1.05) -> bool`
- `assert_no_label_column(dataset_name, label_column="PassOrFail")`

`runtime_assertions.py`:

- `assert_route(actual, expected)`
- `assert_used_columns(actual, expected)`
- `assert_metrics_close(actual, expected)`
- `assert_table_close(actual, expected)`
- `assert_evidence_keys(payload, expected_keys)`
- `assert_answer_contains_terms(answer, terms)`
- `assert_answer_excludes_terms(answer, forbidden_terms)`
- `assert_answerability(answer_quality, expected_status)`
- `assert_no_forbidden_metric_keys(payload, forbidden_metric_keys)`

### Contract test 설계

`contracts/test_p0_moldset_dataset_contract.py`:

- `test_moldset_labeled_shape_and_required_columns()`
- `test_moldset_labeled_label_distribution_oracle()`
- `test_moldset_labeled_defect_rate_by_part_oracle()`
- `test_moldset_labeled_defect_reason_counts_oracle()`

`contracts/test_p1_dataset_contracts.py`:

- `test_unlabeled_data_has_no_pass_or_fail_column()`
- `test_cn7_scaled_like_numeric_columns()`
- `test_rg3_scaled_like_numeric_columns()`
- `test_labeled_data_yn_label_distribution()`

`contracts/test_project_benchmark_cases.py`:

- 모든 P0/P1 case가 `priority`, `dataset`, `question`, `expected_route`를 가진다.
- case의 `dataset`이 `evaluation/raw/`에 존재한다.
- P0는 최소 4개, P1은 최소 4개 scenario를 가진다.
- `expected_used_columns`가 dataset 실제 컬럼에 존재한다. 단, P1-A의 `expected_missing_columns`는 없는 것이 맞다.

### Runtime deterministic test 설계

목적은 LLM/live 전에 core 실행 계층이 raw oracle과 맞는지 확인하는 것이다.

P0 runtime:

- 라벨 분포 분석 결과의 `raw_metrics` 비교
- 제품별 불량률 `table` 비교
- 불량 사유별 건수 `table` 비교
- 전처리 plan/executor 단위에서 scale 대상과 protected column violation 검증

P1 runtime:

- unlabeled dataset에서 label column 없음 감지
- CN7/RG3 mean/std 기반 scaled-like 판단
- `labeled_data.csv`의 `Y/N` count와 비율 계산

주의:

- runtime deterministic test는 외부 LLM 호출 없이 돌아야 한다.
- LLM이 필요한 planner/codegen은 fake plan, fixture, deterministic helper로 우회한다.
- 실패 원인이 LLM 변동성인지 core 계산 오류인지 분리하는 것이 목적이다.

### Workflow branch test 설계

목적은 `builder.py`, `AgentClient`, evidence contract, approval 흐름이 기대 payload를 유지하는지 검증하는 것이다.

P0 workflow:

- analysis 질문 3종이 analysis branch로 들어가는지 확인
- final state에 `analysis_result`, `evidence_package`, `answer_quality`, `node_results`가 있는지 확인
- P0-D preprocess 질문이 `approval_required`로 멈추는지 확인
- approve resume 후 `preprocess_result.status`가 성공 계열인지 확인

P1 workflow:

- unlabeled defect-rate 질문은 analysis branch를 타되 `answer_quality.status`가 unanswerable/limited인지 확인
- scaled detection 질문은 analysis branch와 mean/std evidence를 유지하는지 확인
- `Y/N` 라벨 분포 질문은 used column과 metrics가 evidence에 남는지 확인

주의:

- workflow branch test는 실제 LLM 호출 대신 fake planner/analysis/preprocess service를 사용한다.
- 현재 `backend/tests/test_chat_sse_contract.py`의 fake workflow 패턴과 `backend/tests/test_orchestration_evidence_contract.py`의 evidence assertion 패턴을 재사용한다.

### Live benchmark 설계

`backend/tests/evaluation/live/conftest.py`에서 아래 조건 없이는 skip한다.

```python
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_AGENT_BENCHMARK") != "1",
    reason="set RUN_LIVE_AGENT_BENCHMARK=1 to run live LLM workflow tests",
)
```

Live benchmark는 다음만 검증한다.

- 실제 LangGraph + LLM workflow가 P0/P1 대표 case를 통과하는가?
- final answer가 evidence 기반으로 숫자를 말하는가?
- P1-A처럼 계산 불가능한 질문에서 숫자를 조작하지 않는가?
- trace/SSE event에서 `done`, `evidence_package`, `answer_quality`가 보존되는가?

Live benchmark는 기본 CI gate가 아니라 수동/야간 benchmark로 둔다.

## 구현 반영 순서

1. **P0-A 라벨 분포 dataset contract + oracle helper부터 작성한다.**
   - 가장 작고 실패 원인이 명확하다.
2. **P0-A runtime deterministic test를 붙인다.**
   - route보다 먼저 raw metric oracle을 고정한다.
3. **P0-B/P0-C table oracle을 추가한다.**
   - table accuracy helper를 이때 만든다.
4. **P0-D preprocess approval/protected column test를 추가한다.**
   - route, approval, scale target, protected column violation을 분리해 검증한다.
5. **P1-A answerability negative case를 추가한다.**
   - hallucination 방지 기준을 먼저 고정한다.
6. **P1-B/P1-C scaled detection을 추가한다.**
   - mean/std oracle과 evidence coverage를 검증한다.
7. **P1-D `Y/N` 라벨 정규화를 추가한다.**
   - count는 확정하되 라벨 의미 단정 여부를 별도 체크한다.
8. **마지막에 live benchmark를 opt-in으로 연결한다.**

## 리뷰 체크포인트

- `expected_route`가 실제 workflow branch와 일치하는가?
- `expected_used_columns`가 output/evidence/node result에 grounded되어 있는가?
- 숫자 답변은 raw CSV ground truth와 일치하는가?
- table scenario는 row key와 metric alias 차이를 흡수하되 값은 정확히 비교하는가?
- 라벨 없는 데이터는 불량률을 만들어내지 않고 계산 불가를 설명하는가?
- scaled-like 판단은 mean/std 수치 근거를 남기는가?
- `Y/N` 라벨은 count와 의미를 혼동하지 않는가?
- 전처리 scenario는 approval을 거치고 보호 컬럼을 제외하는가?
- live benchmark는 명시적 opt-in 없이 실행되지 않는가?
