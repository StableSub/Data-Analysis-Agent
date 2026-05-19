# Live E2E Benchmark Finding 01 — Fixture & Environment Gate

## 구현 단위
`backend/tests/evaluation/live/conftest.py`를 readiness-only scaffold에서 실제 `AgentClient` Live E2E를 실행할 수 있는 fixture 계층으로 확장했다.

## 핵심 변경
- `.env` 자동 로드 유지
- `RUN_LIVE_BENCHMARK=1` opt-in gate 유지
- `OPENAI_API_KEY` 확인 추가
- `langchain-openai` provider package 확인 추가
- `BENCHMARK_MODEL_ID`, `BENCHMARK_LIVE_TIMEOUT_SECONDS`, `BENCHMARK_LIVE_CASE_IDS` 지원
- benchmark dataset source mapping 추가
  - raw CSV가 있으면 `benchmark-{dataset-stem}` source_id를 자동 생성
  - 필요 시 `BENCHMARK_SOURCE_ID_*`로 source_id override 가능
- raw path override env mapping 추가
  - `BENCHMARK_RAW_PATH_*`
- temp SQLite DB fixture 추가
  - local `app.db`를 변경하지 않음
  - temp DB에 benchmark `Dataset` rows 등록
  - source id는 `.env`/환경값을 사용
  - storage path는 기본 `evaluation/raw/*.csv`

## 중요한 설계 결정
기존 `build_agent_client(db)`는 service 조립 시 RAG embedder를 즉시 만들고, 현재 환경에는 `sentence_transformers`가 없어 Live 분석 route와 무관하게 실패했다. 그래서 Live fixture는 real `AgentClient`와 real `build_main_workflow`를 사용하되, 분석 테스트에서 쓰지 않는 RAG/Guideline RAG만 no-op service로 대체했다.

이 결정으로 검증 대상은 다음처럼 유지된다.

```text
AgentClient 실제 실행
→ LangGraph main workflow 실제 실행
→ planner/analysis/codegen/sandbox/evidence 실제 경로
→ temp DB DatasetRepository 실제 조회
→ LLM provider가 설치된 환경에서는 실제 LLM 호출
```

## 현재 환경 관찰
현재 `.env`에는 아래 live 관련 key만 확인됐다.

```text
OPENAI_API_KEY
RUN_LIVE_BENCHMARK
```

`BENCHMARK_SOURCE_ID_*` key가 없어도 raw CSV 기준 source_id를 자동 생성한다.
현재 Python 환경에는 `langchain-openai`가 없어 실제 LLM Live 호출은 skip된다.
