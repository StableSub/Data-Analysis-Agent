# Moldset 품질 관리 우선순위 도출 시나리오

## 목적

이 문서는 `moldset_labeled.csv`를 사용하는 가장 적절한 평가/데모 시나리오 하나를 정의한다.

시나리오의 핵심은 품질관리 담당자가 사출성형 생산 데이터를 업로드한 뒤, AI 데이터 분석 에이전트를 통해 전체 품질 현황, 제품별 리스크, 불량 사유, 시간 흐름, 전처리 필요성, 시각화, 리포트를 단계적으로 확인하는 것이다.

각 단계는 기존 질문 문서와 연결한다.

- 분석/전처리 질문: [moldset-analysis-questions.md](./moldset-analysis-questions.md)
- 시각화 질문: [moldset-visualization-questions.md](./moldset-visualization-questions.md)
- 레포트 질문: [moldset-report-questions.md](./moldset-report-questions.md)
- 정량 평가 기준: [quantitative-metrics.md](./quantitative-metrics.md)

## 시나리오 한 줄 요약

품질관리 담당자가 `moldset_labeled.csv`를 업로드하고, AI 에이전트에게 불량 현황과 관리 우선순위를 분석하게 한 뒤, 제품별 불량률 시각화와 품질 현황 리포트까지 생성한다.

## 사용자 상황

사출성형 품질관리 담당자는 최근 생산 데이터에서 불량이 어느 제품과 어떤 사유에 집중되는지 확인해야 한다. 담당자는 Python이나 pandas를 직접 사용하지 않고, Workbench에 `moldset_labeled.csv`를 업로드한 뒤 자연어 질문으로 다음 내용을 확인하려고 한다.

1. 데이터 규모와 핵심 컬럼
2. 전체 정상/불량 라벨 분포
3. 제품별 불량률과 관리 우선순위
4. 불량 사유별 집중 현황
5. 날짜별 불량 발생 패턴
6. 분석 전 전처리 필요성
7. 제품별 불량률 시각화
8. 품질 현황 리포트
9. 데이터만으로 원인을 확정할 수 있는지 여부

## 데이터 기준

이 시나리오는 `moldset_labeled.csv`의 다음 oracle 값을 기준으로 한다.

| 항목 | 기준 값 |
|---|---:|
| 전체 행 수 | 2,607건 |
| 전체 컬럼 수 | 47개 |
| 정상 건수 | 2,555건 |
| 불량 건수 | 52건 |
| 전체 불량률 | 약 1.99% |
| 제품 수 | 4종 |
| 주요 불량 사유 | 가스, 미성형, 초기허용불량 |
| 설비 | `650톤-우진2호기` 단일 설비 |

## 파트별 예상 질문 연결

### 1. 데이터 이해 파트

연결 문서:
- [moldset-analysis-questions.md](./moldset-analysis-questions.md)

사용 질문:

```text
이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.
```

시나리오상 역할:
- 사용자가 업로드한 데이터가 어떤 구조인지 먼저 파악한다.
- 이후 분석 질문에서 사용할 핵심 컬럼을 확인한다.

기대 확인 포인트:
- 2,607행, 47컬럼을 정확히 제시한다.
- `PassOrFail`, `PART_NAME`, `Reason`, `TimeStamp`를 핵심 컬럼으로 언급한다.
- 제조 품질 데이터라는 맥락을 설명한다.
- 존재하지 않는 컬럼을 만들지 않는다.

### 2. 전체 품질 현황 파트

연결 문서:
- [moldset-analysis-questions.md](./moldset-analysis-questions.md)
- [quantitative-metrics.md](./quantitative-metrics.md)

사용 질문:

```text
PassOrFail 라벨 분포를 알려줘.
```

시나리오상 역할:
- 전체 데이터에서 정상과 불량의 비율을 확인한다.
- 이후 제품별/사유별 분석의 기준이 되는 전체 불량 규모를 잡는다.

기대 결과:

| 라벨 | 의미 | 건수 | 비율 |
|---:|---|---:|---:|
| 0 | 정상 | 2,555 | 약 98.01% |
| 1 | 불량 | 52 | 약 1.99% |

기대 확인 포인트:
- 라벨 분포를 모델 정확도나 예측 성능으로 오해하지 않는다.
- 불량 표본이 52건으로 적다는 한계를 이후 해석에 반영한다.

### 3. 제품별 품질 리스크 파트

연결 문서:
- [moldset-analysis-questions.md](./moldset-analysis-questions.md)
- [quantitative-metrics.md](./quantitative-metrics.md)

사용 질문:

```text
제품별 불량률을 계산해줘.
```

시나리오상 역할:
- 어떤 제품에서 품질 리스크가 상대적으로 큰지 확인한다.
- 최종 리포트의 관리 우선순위 근거로 사용한다.

기대 결과:

| 제품명 | 총 생산량 | 불량 건수 | 불량률 |
|---|---:|---:|---:|
| `CN7 W/S SIDE MLD'G LH` | 712 | 9 | 약 1.26% |
| `CN7 W/S SIDE MLD'G RH` | 713 | 18 | 약 2.52% |
| `RG3 MOLD'G W/SHLD, LH` | 591 | 0 | 0.00% |
| `RG3 MOLD'G W/SHLD, RH` | 591 | 25 | 약 4.23% |

기대 확인 포인트:
- 단순 불량 건수가 아니라 제품별 총 생산량 대비 불량률을 계산한다.
- 4개 제품이 모두 포함된다.
- `RG3 MOLD'G W/SHLD, RH`가 가장 높은 리스크 후보로 제시된다.
- 불량률이 높다는 사실을 원인 확정으로 표현하지 않는다.

### 4. 불량 사유 집중 파트

연결 문서:
- [moldset-analysis-questions.md](./moldset-analysis-questions.md)
- [quantitative-metrics.md](./quantitative-metrics.md)

사용 질문:

```text
PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘.
```

시나리오상 역할:
- 어떤 불량 유형이 가장 많이 발생했는지 확인한다.
- 개선 제안에서 우선 점검 항목을 정할 때 사용한다.

기대 결과:

| 불량 사유 | 건수 | 비율 |
|---|---:|---:|
| `가스` | 30 | 약 57.69% |
| `미성형` | 12 | 약 23.08% |
| `초기허용불량` | 10 | 약 19.23% |

기대 확인 포인트:
- 반드시 `PassOrFail=1` 필터를 적용한다.
- 정상 데이터의 `Reason=None` 또는 결측값을 불량 사유로 포함하지 않는다.
- `가스` 불량이 가장 많다는 점을 요약한다.

### 5. 시간 흐름 파트

연결 문서:
- [moldset-analysis-questions.md](./moldset-analysis-questions.md)
- [quantitative-metrics.md](./quantitative-metrics.md)

사용 질문:

```text
날짜별 불량 건수를 분석해줘.
```

시나리오상 역할:
- 불량이 특정 날짜에 집중되는지 확인한다.
- 최종 리포트에서 시간대별 점검 필요성을 언급할 근거로 사용한다.

기대 결과:

| 날짜 | 불량 건수 |
|---|---:|
| `2020-10-16` | 17 |
| `2020-10-22` | 15 |
| `2020-10-23` | 10 |
| `2020-10-27` | 10 |

기대 확인 포인트:
- `TimeStamp`를 날짜 단위로 변환한다.
- `PassOrFail=1`인 행만 불량 건수로 집계한다.
- 전체 생산량 추이와 불량 건수 추이를 혼동하지 않는다.

### 6. 전처리 필요성 파트

연결 문서:
- [moldset-analysis-questions.md](./moldset-analysis-questions.md)

사용 질문 1:

```text
이 데이터에서 분석 전에 전처리가 필요한 부분을 찾아줘.
```

사용 질문 2:

```text
숫자형 공정 컬럼들을 표준화해줘. 라벨과 제품명, 시간 컬럼은 제외해줘.
```

시나리오상 역할:
- 분석에 쓰면 안 되는 식별자/라벨/시간/제품 컬럼을 구분한다.
- 전부 0인 센서 컬럼과 대부분 0인 컬럼을 데이터 품질 이슈로 확인한다.
- 전처리 실행 전 approval 흐름이 필요한지 확인한다.

기대 확인 포인트:
- `_id`, `Unnamed: 0`, `PART_FACT_SERIAL`, `PART_NO` 같은 식별자 컬럼 제외를 언급한다.
- `PassOrFail`, `PART_NAME`, `TimeStamp`, `PART_FACT_PLAN_DATE`를 보호 컬럼으로 취급한다.
- 전부 0인 주요 온도 컬럼을 데이터 품질 이슈로 언급한다.
- 표준화 요청에서는 승인 전 실제 데이터를 변경하지 않는다.

전부 0인 숫자형 컬럼 기준:

```text
Barrel_Temperature_7
Mold_Temperature_1
Mold_Temperature_2
Mold_Temperature_5
Mold_Temperature_6
Mold_Temperature_7
Mold_Temperature_8
Mold_Temperature_9
Mold_Temperature_10
Mold_Temperature_11
Mold_Temperature_12
```

### 7. 시각화 파트

연결 문서:
- [moldset-visualization-questions.md](./moldset-visualization-questions.md)

사용 질문:

```text
제품별 불량률을 막대그래프로 시각화해줘.
```

시나리오상 역할:
- 제품별 관리 우선순위를 시각적으로 보여준다.
- 발표나 데모에서 가장 설명하기 쉬운 단일 차트를 생성한다.

기대 결과:
- 차트 1개
- 차트 유형: bar
- x축: `PART_NAME`
- y축: `defect_rate_pct` 또는 동등한 불량률 값
- 4개 제품이 모두 표시됨
- `RG3 MOLD'G W/SHLD, RH` 막대가 가장 높음

기대 확인 포인트:
- 현재 구현 기준에 맞게 단일 `chart_data` 또는 `charts[0]`만 기대한다.
- 제품별 총 생산량, 불량 건수, 불량률을 한 차트에 무리하게 모두 넣지 않는다.
- 원인 해석은 관련 가능성 수준으로 제한한다.

대체 시각화 질문:

```text
PassOrFail=1인 불량 데이터만 대상으로 Reason별 건수를 막대그래프로 시각화해줘.
```

대체 질문은 불량 사유 중 `가스`가 가장 많다는 메시지를 더 직관적으로 보여주고 싶을 때 사용한다.

### 8. 리포트 파트

연결 문서:
- [moldset-report-questions.md](./moldset-report-questions.md)

사용 질문:

```text
이 데이터의 전체 품질 현황을 요약하는 리포트를 작성해줘. 양품/불량 비율, 불량 사유, 제품별 생산량을 포함해줘.
```

시나리오상 역할:
- 앞 단계의 분석 결과를 실무자가 읽을 수 있는 품질 현황 리포트로 정리한다.
- 데이터 개요, 불량 현황, 제품별 차이, 주요 불량 사유, 데이터 품질 이슈, 개선 방향을 하나의 결과물로 묶는다.

좋은 리포트 기준:
- 전체 2,607건과 불량 52건을 기준으로 설명한다.
- 전체 불량률이 약 2% 수준임을 제시한다.
- `가스`가 가장 많은 불량 사유임을 설명한다.
- 제품별 총 생산량과 불량률을 함께 고려한다.
- 전부 0인 온도 컬럼 등 데이터 품질 이슈를 언급한다.
- 실무 점검 항목을 제안한다.
- 불량 원인을 확정하지 않는다.

### 9. 한계 확인 파트

연결 문서:
- [moldset-analysis-questions.md](./moldset-analysis-questions.md)
- [moldset-report-questions.md](./moldset-report-questions.md)

사용 질문:

```text
이 데이터만으로 불량 원인을 확정할 수 있어?
```

시나리오상 역할:
- AI 답변이 과도하게 단정하지 않는지 확인한다.
- 데이터 분석 결과와 실제 공정 원인 규명의 차이를 구분한다.

기대 답변 방향:
- 현재 데이터만으로 불량 원인을 확정할 수 없다고 답한다.
- 제품별 불량률, 불량 사유, 날짜별 집중은 원인 후보 탐색 근거라고 설명한다.
- 불량 표본 수가 52건으로 작다는 한계를 언급한다.
- 추가로 설비 세팅 변경 이력, 작업자/교대 정보, 원재료 정보, 금형 점검 이력, 센서 정상 여부가 필요하다고 제안한다.

## 최종 데모 순서

| 순서 | 파트 | 질문 | 연결 문서 | 주요 검증 포인트 |
|---:|---|---|---|---|
| 1 | 데이터 이해 | `이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.` | [분석/전처리](./moldset-analysis-questions.md) | 2,607행, 47컬럼, 핵심 컬럼 인식 |
| 2 | 전체 현황 | `PassOrFail 라벨 분포를 알려줘.` | [분석/전처리](./moldset-analysis-questions.md), [정량 지표](./quantitative-metrics.md) | 정상 2,555건, 불량 52건 |
| 3 | 제품별 리스크 | `제품별 불량률을 계산해줘.` | [분석/전처리](./moldset-analysis-questions.md), [정량 지표](./quantitative-metrics.md) | 제품별 총량 대비 불량률 계산 |
| 4 | 불량 사유 | `PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘.` | [분석/전처리](./moldset-analysis-questions.md), [정량 지표](./quantitative-metrics.md) | 정상 Reason 제외, 가스 30건 |
| 5 | 시간 흐름 | `날짜별 불량 건수를 분석해줘.` | [분석/전처리](./moldset-analysis-questions.md), [정량 지표](./quantitative-metrics.md) | 날짜 버킷팅, 불량만 집계 |
| 6 | 전처리 | `이 데이터에서 분석 전에 전처리가 필요한 부분을 찾아줘.` | [분석/전처리](./moldset-analysis-questions.md) | 보호 컬럼, 전부 0인 컬럼 식별 |
| 7 | 전처리 승인 | `숫자형 공정 컬럼들을 표준화해줘. 라벨과 제품명, 시간 컬럼은 제외해줘.` | [분석/전처리](./moldset-analysis-questions.md) | approval 요청, 보호 컬럼 제외 |
| 8 | 시각화 | `제품별 불량률을 막대그래프로 시각화해줘.` | [시각화](./moldset-visualization-questions.md) | 단일 bar chart, 4개 제품 표시 |
| 9 | 리포트 | `이 데이터의 전체 품질 현황을 요약하는 리포트를 작성해줘. 양품/불량 비율, 불량 사유, 제품별 생산량을 포함해줘.` | [레포트](./moldset-report-questions.md) | 수치 기반 요약, 개선 제안, 원인 단정 방지 |
| 10 | 한계 확인 | `이 데이터만으로 불량 원인을 확정할 수 있어?` | [분석/전처리](./moldset-analysis-questions.md), [레포트](./moldset-report-questions.md) | 제한 답변, 추가 데이터 필요성 |

## 평가 관점

이 시나리오는 다음 능력을 한 번에 검증한다.

| 평가 관점 | 확인할 동작 |
|---|---|
| 데이터 grounding | 실제 컬럼명과 행/컬럼 수를 정확히 사용하는가 |
| 필터링 | `PassOrFail=1` 조건이 필요한 질문에서 정상 데이터를 제외하는가 |
| 그룹화 | 제품별, 사유별, 날짜별 집계를 정확히 수행하는가 |
| 비율 계산 | 제품별 총 생산량을 분모로 불량률을 계산하는가 |
| 데이터 품질 진단 | 전부 0인 컬럼과 보호 컬럼을 구분하는가 |
| approval 흐름 | 전처리 실행 전 사용자 승인을 요구하는가 |
| 시각화 계약 | 한 질문당 단일 chart artifact로 응답하는가 |
| 리포트 품질 | 숫자, 해석, 한계, 개선 제안을 구조화하는가 |
| 과잉 추론 방지 | 불량 원인을 확정하지 않고 관련 가능성으로 표현하는가 |

## 이 시나리오에서 제외하는 요구

아래 요구는 현재 시나리오의 범위에서 제외한다.

- 불량 예측 모델 학습
- 모델 정확도, F1 score, feature importance 평가
- 여러 차트를 한 질문에서 동시에 생성
- 히트맵, 박스플롯, 바이올린 플롯 등 현재 안정 검증 범위를 넘는 시각화
- 외부 기준값 없이 정상 공정 범위 단정
- 데이터만으로 불량 원인 확정
- 기존 분석 결과 또는 baseline 결과와의 자동 비교

## 발표용 요약 문장

`moldset_labeled.csv` 시나리오는 단순 CSV 요약이 아니라, 품질관리 담당자가 실제로 물을 법한 질문 흐름을 기준으로 구성했다. AI 에이전트는 데이터 구조 확인, 라벨 분포, 제품별 불량률, 불량 사유, 날짜별 집중 구간, 전처리 필요성, 단일 시각화, 리포트 작성까지 단계적으로 수행한다. 최종적으로는 `RG3 MOLD'G W/SHLD, RH` 제품과 `가스` 불량을 주요 관리 후보로 제시하되, 데이터만으로 원인을 확정하지 않고 추가 공정 정보가 필요하다는 한계를 함께 설명해야 한다.
