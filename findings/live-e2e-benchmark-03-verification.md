# Live E2E Benchmark Finding 03 — Verification

## 검증 명령 1: 전체 evaluation suite

```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/contracts backend/tests/evaluation/metrics backend/tests/evaluation/runtime backend/tests/evaluation/workflow backend/tests/evaluation/live
```

결과:

```text
29 passed, 4 skipped in 1.78s
```

## 검증 명령 2: 기존 SSE/evidence smoke

```bash
PYTHONPATH=. pytest -q backend/tests/test_orchestration_evidence_contract.py backend/tests/test_chat_sse_contract.py
```

결과:

```text
44 passed in 0.57s
```

## 추가 Live preflight 확인
source id를 임시 주입해 P0 AgentClient Live test를 호출했다.

```bash
BENCHMARK_SOURCE_ID_MOLDSET_LABELED=benchmark-moldset-labeled \
PYTHONPATH=. pytest -q backend/tests/evaluation/live/test_agent_client_live_p0.py -s
```

결과:

```text
1 skipped in 0.01s
```

skip 사유:
- 현재 환경에 `langchain-openai` package가 없어 실제 LLM provider 초기화가 불가능함

## 완료 판단
코드 레벨 구현은 완료됐다. 현재 환경에서는 external Live 실행이 아래 조건 부족으로 skip된다.

- `langchain-openai` 미설치
- `.env`에 `BENCHMARK_SOURCE_ID_*`가 없어도 raw CSV 기준 source_id를 자동 생성하도록 수정됨

해당 조건을 채우면 같은 테스트가 실제 `AgentClient` + LLM-backed workflow + evidence oracle 검증을 수행한다.
