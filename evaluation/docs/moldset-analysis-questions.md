# Moldset 분석/전처리 테스트 질문

## 목적

이 문서는 `evaluation/raw/moldset_labeled.csv`를 대표 데이터셋으로 사용해, 시각화·레포트 이전 단계의 핵심 질문을 정리한다.

평가 핵심은 사용자가 데이터셋을 이해하고 분석을 시작할 수 있도록, 데이터 이해, 전처리 판단, 분석 실행, 근거 확인 질문을 제공하는 것이다.

## 데이터 확인 기준

- 전체 행 수: 2,607건
- 전체 컬럼 수: 47개
- 정상: 2,555건
- 불량: 52건
- 불량률: 약 1.99%
- 제품: 4종
  - `CN7 W/S SIDE MLD'G LH`: 712건, 불량 9건, 불량률 약 1.26%
  - `CN7 W/S SIDE MLD'G RH`: 713건, 불량 18건, 불량률 약 2.52%
  - `RG3 MOLD'G W/SHLD, LH`: 591건, 불량 0건, 불량률 0.00%
  - `RG3 MOLD'G W/SHLD, RH`: 591건, 불량 25건, 불량률 약 4.23%
- 불량 사유:
  - `가스`: 30건
  - `미성형`: 12건
  - `초기허용불량`: 10건
- 날짜별 불량 건수:
  - `2020-10-16`: 17건
  - `2020-10-22`: 15건
  - `2020-10-23`: 10건
  - `2020-10-27`: 10건
- 전부 0인 주요 컬럼:
  - `Barrel_Temperature_7`
  - `Mold_Temperature_1`, `Mold_Temperature_2`, `Mold_Temperature_5`~`Mold_Temperature_12`
- 보호/제외 우선 컬럼:
  - `_id`, `Unnamed: 0`, `PART_FACT_SERIAL`, `PART_NO`, `PART_NAME`, `TimeStamp`, `PART_FACT_PLAN_DATE`, `PassOrFail`

## 추천 질문

### 1. 데이터셋 기본 구조 확인

질문:
- 이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.

기대 route:
- `analysis` 또는 metadata fast path

기대 used columns:
- 전체 metadata 중심

확인 포인트:
- 2,607행, 47컬럼을 정확히 제시한다.
- `PassOrFail`, `PART_NAME`, `Reason`, `TimeStamp`를 핵심 컬럼으로 언급한다.
- 존재하지 않는 컬럼을 만들지 않는다.

### 2. 라벨 분포 분석

질문:
- PassOrFail 라벨 분포를 알려줘.

기대 route:
- `analysis`

기대 used columns:
- `PassOrFail`

기대 결과:
- 정상 2,555건
- 불량 52건
- 불량률 약 1.99%

확인 포인트:
- 라벨 분포를 모델 정확도나 예측 성능으로 오해하지 않는다.
- 정상/불량 불균형을 설명한다.

### 3. 제품별 불량률 분석

질문:
- 제품별 불량률을 계산해줘.

기대 route:
- `analysis`

기대 used columns:
- `PART_NAME`
- `PassOrFail`

기대 결과:
- `RG3 MOLD'G W/SHLD, RH`가 약 4.23%로 가장 높다.
- `RG3 MOLD'G W/SHLD, LH`는 불량 0건이다.
- 4개 제품이 모두 포함된다.

확인 포인트:
- 단순 불량 건수가 아니라 제품별 총 생산량 대비 불량률을 계산한다.
- 없는 제품명을 만들지 않는다.

### 4. 불량 사유별 건수 분석

질문:
- PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘.

기대 route:
- `analysis`

기대 used columns:
- `PassOrFail`
- `Reason`

기대 결과:
- `가스`: 30건
- `미성형`: 12건
- `초기허용불량`: 10건

확인 포인트:
- 표준 benchmark 질문은 `PassOrFail=1` 필터를 포함한 명시형 문장을 사용한다.
- 정상 데이터의 `Reason=None`을 불량 사유로 포함하지 않는다.
- 반드시 `PassOrFail=1` 필터를 적용한다.

### 5. 날짜별 불량 발생 분석

질문:
- 날짜별 불량 건수를 분석해줘.

기대 route:
- `analysis`

기대 used columns:
- `TimeStamp`
- `PassOrFail`

기대 결과:
- `2020-10-16`: 17건
- `2020-10-22`: 15건
- `2020-10-23`: 10건
- `2020-10-27`: 10건

확인 포인트:
- `TimeStamp`를 날짜 단위로 변환한다.
- 전체 생산량 추이가 아니라 불량 건수 분석에 집중한다.

### 6. 전처리 필요성 진단

질문:
- 이 데이터에서 분석 전에 전처리가 필요한 부분을 찾아줘.

기대 route:
- `preprocess` 또는 preprocess recommendation

기대 used columns:
- 결측/0값/상수 컬럼 관련 전체 profile

기대 결과:
- 식별자 컬럼 제외 필요성을 언급한다.
- 전부 0인 온도 컬럼을 데이터 품질 이슈로 언급한다.
- 대부분 0인 `Switch_Over_Position`을 점검 대상으로 언급한다.

확인 포인트:
- 전처리를 바로 적용하지 않고 계획 또는 추천 형태로 제시한다.
- 라벨, 시간, 제품명 같은 보호 컬럼을 변환 대상으로 잡지 않는다.

### 7. 숫자형 공정 컬럼 표준화 요청

질문:
- 숫자형 공정 컬럼들을 표준화해줘. 라벨과 제품명, 시간 컬럼은 제외해줘.

기대 route:
- `preprocess`

기대 approval:
- `approval_required`

보호 컬럼:
- `PassOrFail`
- `PART_NAME`
- `PART_NO`
- `PART_FACT_SERIAL`
- `_id`
- `Unnamed: 0`
- `TimeStamp`
- `PART_FACT_PLAN_DATE`

확인 포인트:
- 전처리 적용 전 사용자 승인을 요청한다.
- 보호 컬럼을 scale 대상에 포함하지 않는다.
- 승인 전 실제 데이터를 변경하지 않는다.

### 8. 공정 변수 관계 분석

질문:
- Max_Injection_Pressure와 Cycle_Time의 관계를 분석해줘.

기대 route:
- `analysis`

기대 used columns:
- `Max_Injection_Pressure`
- `Cycle_Time`

확인 포인트:
- 두 컬럼이 실제 존재하는지 검증한다.
- 상관 가능성을 설명하되 원인을 단정하지 않는다.
- 필요 이상으로 모델 학습이나 예측 성능을 언급하지 않는다.

### 9. 분석 근거 확인

질문:
- 방금 분석에 사용된 컬럼과 계산 근거를 설명해줘.

기대 route:
- `analysis` 또는 `data_qa`

기대 확인 대상:
- `used_columns`
- `analysis_result`
- `evidence_package`
- `answer_quality`

확인 포인트:
- 사용 컬럼을 명시한다.
- 계산 기준과 필터 조건을 설명한다.
- 근거가 부족한 내용은 단정하지 않는다.

### 10. 답변 불가능/제한 확인 질문

질문:
- 이 데이터만으로 불량 원인을 확정할 수 있어?

기대 route:
- `analysis` 또는 `data_qa`

기대 답변 상태:
- `limited` 또는 제한 조건을 포함한 답변

확인 포인트:
- 불량 원인을 확정한다고 말하지 않는다.
- 관찰된 관련 가능성과 추가 검증 필요성을 구분한다.
- 불량 표본 수 52건이라는 한계를 언급한다.

## 우선 테스트 질문 TOP 5

1. PassOrFail 라벨 분포를 알려줘.
2. 제품별 불량률을 계산해줘.
3. PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘.
4. 이 데이터에서 분석 전에 전처리가 필요한 부분을 찾아줘.
5. 숫자형 공정 컬럼들을 표준화해줘. 라벨과 제품명, 시간 컬럼은 제외해줘.

## 평가 체크리스트

- [ ] 질문이 시각화/레포트 이전의 분석 시작점으로 적절하다.
- [ ] 실제 존재하는 컬럼만 사용한다.
- [ ] `PassOrFail`, `PART_NAME`, `Reason`, `TimeStamp` grounding이 정확하다.
- [ ] count/rate 값이 raw CSV oracle과 일치한다.
- [ ] 전처리 질문은 approval/resume 흐름을 기대한다.
- [ ] 보호 컬럼을 전처리 대상으로 포함하지 않는다.
- [ ] 불량 원인을 확정하지 않고 관련 가능성으로 표현한다.
- [ ] 답변 근거와 한계를 설명한다.

## 현재 단계에서 제외하는 질문

- 모델 학습 정확도, F1 score, 예측 성능을 요구하는 질문
- 여러 차트와 리포트를 한 번에 요구하는 질문
- 원인 확정을 요구하는 질문
- 데이터에 없는 설비/공정/작업자 정보를 묻는 질문
- 외부 기준값 없이 정상 공정 범위를 단정하는 질문
