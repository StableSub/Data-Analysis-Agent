# P0/P1 Benchmark Finding 01 — Assets & Contracts

## 단위 목표
`evaluation/docs/dataset-recommended-scenarios-core.md`의 P0/P1 추천 시나리오를 테스트 가능한 벤치마크 케이스로 고정했다.

## 산출물
- `evaluation/cases/p0_moldset_analysis_cases.jsonl`
  - PassOrFail 분포
  - 제품별 불량률
  - 불량 사유별 건수
- `evaluation/cases/p0_moldset_preprocess_cases.jsonl`
  - 공정 수치 컬럼 표준화 + 라벨/식별자 보호
- `evaluation/cases/p1_dataset_quality_cases.jsonl`
  - unlabeled defect-rate abstain
  - CN7/RG3 scaled-like detection
  - Y/N 라벨 분포
- `backend/tests/evaluation/contracts/*`
  - raw CSV shape, label distribution, expected table oracle 검증

## 핵심 기준값
- `moldset_labeled.csv`: 2,607 rows, 47 columns
- P0 PassOrFail: 정상 2,555 / 불량 52 / 불량률 1.9946298427%
- P0 제품별 최고 불량률: `RG3 MOLD'G W/SHLD, RH` 25/591 = 4.2301184433%
- P0 불량 사유: 가스 30, 미성형 12, 초기허용불량 10
- P1 `unlabeled_data.csv`: 795,315 rows, `PassOrFail` 없음
- P1 `labeled_data.csv`: Y 7,925 / N 71 / N rate 0.887943972%

## 검증 evidence
```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/contracts
```

통합 실행에서 계약 테스트 포함 전체 evaluation suite가 통과했다: `29 passed, 2 skipped`.

## 판단
P0는 “route 값만 검증”이 아니라, **정답 계산 가능한 데이터 오라클**을 함께 잠근다. P1은 계산 불가능/스케일 상태/라벨 체계 차이를 명시해 Live 전 로직 테스트의 기준을 만든다.
