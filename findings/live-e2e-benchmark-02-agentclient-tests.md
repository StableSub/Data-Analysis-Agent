# Live E2E Benchmark Finding 02 — AgentClient Live Tests

## 구현 단위
`backend/tests/evaluation/live`에 실제 `AgentClient.astream_with_trace(...)`를 호출하는 P0/P1 Live 테스트를 추가했다.

## 추가 파일
- `backend/tests/evaluation/live/test_agent_client_live_p0.py`
- `backend/tests/evaluation/live/test_agent_client_live_p1.py`

## P0 Live 테스트
대상 case file:
- `evaluation/cases/p0_moldset_analysis_cases.jsonl`

지원 case:
- `p0_moldset_label_distribution`
- `p0_moldset_defect_rate_by_part`
- `p0_moldset_defect_reason_counts`

검증 항목:
- `AgentClient` done event 존재
- error event 없음
- `output_type == "data_qa"`
- forbidden model-performance terms 없음
- `answer_quality.status in {"answerable", "limited"}`
- `evidence_package.source_id` 일치
- `evidence_package.used_columns` 검증
- `analysis_metrics` 또는 `analysis_table`을 deterministic oracle과 비교

## P1 Live 테스트
대상 case file:
- `evaluation/cases/p1_dataset_quality_cases.jsonl`

지원 case:
- `p1_unlabeled_defect_rate_abstain`
- `p1_cn7_scaled_detection`
- `p1_rg3_scaled_detection`
- `p1_labeled_data_yn_label_distribution`

검증 항목:
- unlabeled defect-rate는 `unanswerable` 또는 의미 있는 analysis/planning error 허용
- forbidden metric keys absence 검증
- scaled detection은 `used_columns`와 `scaled_like` evidence 또는 답변 문맥 검증
- Y/N label distribution은 `analysis_metrics`의 `total_count`, `y_count`, `n_count` 검증

## 실행 방식
기본 selected case는 비용 제어를 위해 다음 1개다.

```text
p0_moldset_label_distribution
```

확장하려면 `.env`에 지정한다.

```env
BENCHMARK_LIVE_CASE_IDS=p0_moldset_label_distribution,p0_moldset_defect_rate_by_part,p0_moldset_defect_reason_counts,p1_unlabeled_defect_rate_abstain
```
