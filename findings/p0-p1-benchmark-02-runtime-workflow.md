# P0/P1 Benchmark Finding 02 — Runtime & Workflow Gate

## 단위 목표
Live 실행 전에도 현재 코드에서 계산 가능한 부분을 deterministic runtime/workflow gate로 검증하도록 구성했다.

## 테스트 구조
- `backend/tests/evaluation/runtime/`
  - `AnalysisProcessor.validate_execution_result`가 P0 오라클 payload를 정상 결과로 수용하는지 검증
  - `PreprocessProcessor.apply_operations`가 수치 공정 컬럼만 표준화하고 라벨/식별자를 건드리지 않는지 검증
  - P1 unlabeled/scaled/Y-N 라벨 계약을 runtime assertion으로 검증
- `backend/tests/evaluation/workflow/`
  - `build_evidence_contract`가 `source_id`, `used_columns`, `analysis_metrics/table`, `answer_quality`를 전달하는지 검증
  - `AgentClient.astream_with_trace`가 done/approval_required event에 evidence와 approval metadata를 보존하는지 검증
- `backend/tests/evaluation/metrics/`
  - route accuracy, answerability accuracy, column grounding F1, evidence coverage, forbidden term violation, protected-column violation, scaled detection accuracy 검증
- `backend/tests/evaluation/live/`
  - `RUN_LIVE_BENCHMARK=1`일 때만 실행되는 opt-in scaffold

## Live 전/후 역할 분리
| 단계 | 목적 | 기본 CI 포함 여부 |
|---|---|---|
| Contract | raw dataset shape/oracle 고정 | 예 |
| Runtime | 코드의 계산/검증 레이어 확인 | 예 |
| Workflow | evidence/SSE/approval 계약 확인 | 예 |
| Live | 실제 LLM+업로드 dataset source 기반 end-to-end 확인 | 아니오, opt-in |

## 검증 evidence
```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/contracts backend/tests/evaluation/metrics backend/tests/evaluation/runtime backend/tests/evaluation/workflow backend/tests/evaluation/live
# 29 passed, 2 skipped in 2.33s

PYTHONPATH=. pytest -q backend/tests/test_orchestration_evidence_contract.py backend/tests/test_chat_sse_contract.py
# 44 passed in 0.95s
```

## 리스크
Live full workflow는 현재 raw CSV의 업로드된 `source_id`와 외부 LLM credential이 필요하므로 기본 gate에 넣지 않았다. 대신 env-gated scaffold로 분리해, 운영/수동 벤치마크에서만 실행하도록 했다.
