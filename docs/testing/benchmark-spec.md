# 벤치마크 스펙

## 목적

캡스톤 발표에서 “이 시스템이 얼마나 잘 동작하는가”를 수치로 설명하기 위한 최소 평가 규격을 정의한다.
현재 저장소에는 자동 benchmark runner가 없으므로, 이 문서는 **발표 전 수동 또는 반수동 측정 기준**을 먼저 고정하는 역할을 한다.

## 현재 상태

- 단위/회귀 테스트는 일부 존재한다
- 제품 수준 benchmark harness는 아직 없다
- `LLMGateway` 지연시간 집계 대시보드나 `pytest -m benchmark` 체계는 아직 없다

따라서 이 문서는 “이미 자동화된 체계”를 설명하지 않는다.

## 발표 전 최소 측정 목표

### 1. Routing 정확도

- 대상: 20~30개 질문
- 라벨: `general_question`, `data_pipeline` 수준의 주요 분기
- 결과물: confusion matrix 1장

### 2. Analysis 성공률

- 대상: 10~15개 데이터셋 기반 분석 질문
- 측정:
  - 실행 성공/실패
  - 기대한 핵심 지표가 답변에 포함되는지
  - repair 후 회복 여부

### 3. Approval 흐름 검증률

- 대상: preprocess / visualization / report 각 2건 이상
- 측정:
  - `approval_required` 발생 여부
  - approve/revise/cancel 후 기대 경로로 이어지는지

### 4. 응답 지연시간

- 대상: 대표 데모 시나리오 3~5건
- 측정:
  - 첫 `session` 수신까지 시간
  - 첫 `chunk` 수신까지 시간
  - 최종 `done`까지 총 시간

## 케이스 구성 규칙

### Routing 세트

질문 유형을 고르게 섞는다.

- 일반 설명형 질문
- 데이터셋 없이 물어보는 질문
- 데이터셋 기반 분석 질문
- 시각화 요청 포함 질문
- 리포트 요청 포함 질문

### Analysis 세트

각 케이스는 다음을 함께 남긴다.

- 사용 데이터셋
- 질문 원문
- 기대 route
- 기대 핵심 컬럼 또는 지표
- 정답 근거(수작업 계산 또는 기존 결과)
- 성공 판정 기준

### Approval 세트

각 stage별로 다음을 기록한다.

- 어떤 입력이 approval을 유도했는가
- approve/revise/cancel 중 무엇을 테스트했는가
- 기대한 후속 결과가 무엇인가

## 결과 기록 포맷

권장 CSV/시트 컬럼:

| case_id | category | dataset | question | expected | actual | pass | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

권장 summary 지표:

- routing accuracy
- analysis success rate
- repair success rate
- approval flow success rate
- median / max end-to-end latency

## 수집 방법

### 현재 가능한 방법

- 수동 실행 + 결과 시트 기록
- 필요 시 `trace_id`, `session_id`, `run_id`를 함께 보관
- 프론트 데모 기준이면 화면 기록 또는 스크린샷 첨부

### 향후 자동화 후보

- `backend/tests/benchmark/` 케이스 디렉터리
- workflow 직접 호출 runner
- stage latency 집계 스크립트

이 항목은 계획이며, 현재 구현 완료 상태로 발표하지 않는다.

## PASS 기준

발표 전 최소 권장선:

- routing accuracy: 80% 이상
- analysis success rate: 70% 이상
- approval flow success rate: stage별 치명적 실패 0건
- 대표 데모 시나리오: 리허설 3회 연속 완주

위 수치는 팀 내부 발표 기준선이다. 외부 논문 수준의 엄밀한 벤치마크라고 주장하지 않는다.

## 운영 체크리스트

- [ ] 케이스 수와 범주가 충분히 분산되어 있는가
- [ ] 정답 기준이 사람 검토로 재현 가능한가
- [ ] 실패 케이스도 숨기지 않고 기록했는가
- [ ] 발표 슬라이드에서 현재 수치와 향후 자동화 계획을 구분했는가

## 발표용 framing

발표에서는 “정량 평가를 이미 완전 자동화했다”가 아니라,
**테스트셋을 정의하고 반복 측정 가능한 기준을 세웠다**는 점을 강조한다.
가장 중요한 슬라이드는 accuracy 숫자 하나보다, 질문 유형·성공률·실패 원인을 함께 보여주는 요약표다.
