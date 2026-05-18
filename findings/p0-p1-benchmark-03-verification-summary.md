# P0/P1 Benchmark Finding 03 — Verification Summary

## 완료된 구현 단위
1. P0/P1 케이스 manifest 생성
2. raw dataset oracle helper 작성
3. contract/runtime/workflow/metric/live test layout 추가
4. `evaluation/raw/`를 git ignore 처리하고, `evaluation/docs`, `evaluation/cases`, `backend/tests/evaluation`, `findings`는 커밋 가능하도록 예외 처리
5. deterministic benchmark suite 실행 및 통과 확인
6. 기존 SSE/evidence contract smoke test 통과 확인

## 커밋
- `2fdf83e Ground P0/P1 benchmarks in deterministic fixtures`

## 검증 명령
```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/contracts backend/tests/evaluation/metrics backend/tests/evaluation/runtime backend/tests/evaluation/workflow backend/tests/evaluation/live
PYTHONPATH=. pytest -q backend/tests/test_orchestration_evidence_contract.py backend/tests/test_chat_sse_contract.py
```

## 결과
- Evaluation suite: `29 passed, 2 skipped`
- Existing SSE/evidence smoke: `44 passed`

## 남은 범위
- `RUN_LIVE_BENCHMARK=1` + `OPENAI_API_KEY` + 업로드된 benchmark `source_id`를 사용한 실제 Live E2E는 별도 수동/환경 의존 검증으로 남겨두었다.
- raw CSV는 256MB 규모의 local artifact이므로 커밋하지 않았다.
