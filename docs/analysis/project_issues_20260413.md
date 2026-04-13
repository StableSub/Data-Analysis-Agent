# 데이터 분석 AI Agent — 프로젝트 이슈 분석 보고서

> 작성일: 2026-04-13  
> 분석 범위: `docs/reference/capstone-presentation-analysis.md` + 현재 코드베이스  
> 분석 방식: 백엔드 AI 로직 에이전트 + 프론트엔드/통합 에이전트 병렬 분석  

---

## 목차

1. [Critical] 백엔드 AI 로직
2. [High] 백엔드 AI 로직
3. [High] 프론트엔드 & 통합
4. [Medium] 개선 권고
5. 우선순위 로드맵
6. Open Questions

---

## [Critical] 백엔드 AI 로직 이슈

### C-1. Self-reflection / Critique 루프 부재

**현재 상태:**
- `AnalysisService._run_code_generation_loop` (service.py:339-453)가 `max_retries=1` 고정, 단순 반복 루프만 수행
- 실패 시 `repair_analysis_code`에 이전 코드 + 에러 문자열만 전달 — 에러의 구조적 원인 분석·Plan 수정·전략 변경 단계 없음
- `processor.validate_execution_result`는 실패 여부만 판단, "왜 실패했는가"를 분류해 루프에 반영하지 않음

**문제점:**
- 동일 plan 결함(잘못 grounded된 column)이 반복돼 재시도가 낭비됨
- Plan-level 오류(column 매핑, 집계 불가)와 code-level 오류(문법, print 누락)가 모두 `code_repair`로만 흘러감
- "self-healing Agent"를 주장하기엔 구조적 근거 부족

**권장 수정 사항:**
1. `_run_code_generation_loop` 내부에 `critique` 노드 삽입 — 실패 원인을 `column_error | logic_error | timeout | sandbox_violation | contract_violation`로 분류
2. 분류 결과에 따라 분기:
   - `column_error` → `resolve_analysis_plan`부터 재수행 (ground_columns 재실행)
   - `logic_error` → `repair_analysis_code` (기존 루프)
   - `timeout` → 데이터 샘플링 전략 후 재시도
   - `contract_violation` → 코드 템플릿 보강 후 재시도
3. `max_retries`를 원인별 독립 카운터로 분리 (예: plan_retry=1, code_retry=2)
4. 각 reflection 단계를 trace step으로 기록 → 발표 시연 근거 확보

**관련 파일:**
- `backend/app/modules/analysis/service.py` (339-453)
- `backend/app/modules/analysis/processor.py` (validate_execution_result, 400-435)
- `backend/app/modules/analysis/run_service.py`

---

### C-2. Summary ↔ Raw Metrics/Table 간 Hallucination Guard 부재

**현재 상태:**
- `processor._validate_output_payload` (processor.py:475-535)는 스키마 수준 검증만 수행 — summary 텍스트가 `raw_metrics` / `table` 값과 수치적으로 일관되는지 cross-check 없음
- `answer_context`는 근거를 모아두기만 할 뿐, 근거와 서술의 일치 여부 검증 없음

**문제점:**
- LLM이 "매출이 전월 대비 18% 증가"라고 써도 table에 해당 수치가 없으면 그대로 통과
- 데모 중 수치·텍스트 불일치 발생 시 "AI Agent 신뢰성" 주장이 무너짐

**권장 수정 사항:**
1. `processor.py`에 `_verify_summary_consistency(payload, plan)` 헬퍼 추가:
   - summary 텍스트에서 숫자/퍼센트를 정규식 추출
   - 추출된 숫자가 `raw_metrics` 또는 `table` metric 값 집합 내 허용 오차(±1%) 내에 존재하는지 검증
   - 불일치 시 `result_validation` stage error 생성, repair 루프 진입
2. LLM judge 단계(`summary_critic`) 독립 critique 노드로 분리 — consistency score(0~1) 반환, threshold 미만이면 재생성

**관련 파일:**
- `backend/app/modules/analysis/processor.py` (475-535)
- `backend/app/modules/analysis/service.py` (411-429)
- `backend/app/orchestration/state.py` (AnswerPrimaryEvidencePayload)

---

### C-3. 정량적 평가 프레임워크 부재

**현재 상태:**
- 단위 guard 테스트(`test_planner_analysis_accuracy_guards.py`)는 있으나 end-to-end 정확도 벤치마크 harness 없음
- `LLMGateway._log_call` (llm_gateway.py:117-141)은 `duration_ms`를 수집하나 집계·리포트 파이프라인 없음
- routing accuracy, column grounding precision, answer correctness, repair success rate 지표 모두 미정의

**문제점:**
- 캡스톤 발표에서 "얼마나 잘 되는가?"에 수치로 답 불가 → 전형적 감점 사유
- 프롬프트 변경 시 영향 수치화 불가, 리그레션 탐지 불가능

**권장 수정 사항:**
1. `backend/tests/benchmark/` 디렉터리 신설:
   - `routing_cases.yaml`: 20~30개 질문 + 기대 route 라벨 → planner confusion matrix
   - `analysis_cases.yaml`: 10~15개 분석 질문 + ground truth → 실행 성공률·결과 정확도
   - `rag_cases.yaml`: hit-rate 측정용
2. `scripts/run_benchmark.py`: 테스트셋 순회하며 main workflow 직접 호출, 각 지표를 JSON 리포트로 저장
3. `scripts/aggregate_trace.py`: stage별 p50/p95 latency 집계
4. `pytest -m benchmark`로 수동 실행 가능하게 마커 추가

**관련 파일:**
- `backend/tests/test_planner_analysis_accuracy_guards.py`
- `backend/app/core/ai/llm_gateway.py` (117-141)

---

## [High] 백엔드 AI 로직 이슈

### H-1. Codegen Strategy Fallback (Python ↔ SQL) 부재

**현재 상태:**
- `processor._resolve_codegen_strategy` (processor.py:307-328)에서 `sql` 또는 `llm_codegen` 중 하나가 사전 고정됨
- SQL 실패 시 바로 `final_status="fail"` — SQL → Python, Python → SQL 폴백 경로 없음

**문제점:**
- SQL 엔진(duckdb)이 dtype 미스매치로 멈추거나, Python codegen이 복잡한 group-by 계산에서 실패해도 대안 전략 시도 없이 분석 전체가 중단됨

**권장 수정 사항:**
1. `_run_code_generation_loop`를 `run_strategies: list[Literal["sql","python"]]`를 받도록 리팩터링
2. 기본 전략 실패 시 다음 전략으로 전환, `codegen_strategy_switched` 이벤트를 trace에 기록
3. Strategy 간 전환은 1회만 허용 (폴백 무한루프 방지)

**관련 파일:**
- `backend/app/modules/analysis/service.py` (356-453)
- `backend/app/modules/analysis/processor.py` (307-328)
- `backend/app/modules/analysis/sql_executor.py`

---

### H-2. Token/Context 관리 전략 부재 (대용량 Dataset 취약)

**현재 상태:**
- `PlannerService._build_decision`에서 `dataset_context.model_dump()`를 JSON dump하여 프롬프트에 전부 포함 (planner/service.py:192-206)
- `LLMGateway`에 토큰 사용량 추적·경고·압축 로직 전혀 없음

**문제점:**
- 컬럼 200개 이상이거나 dtypes/identifiers가 큰 경우 context window 초과 위험
- PII 포함 가능성 있는 sample 값이 프롬프트로 그대로 전달됨

**권장 수정 사항:**
1. `LLMGateway`에 `token_usage`(prompt_tokens, completion_tokens) 추적 추가 — LangChain callbacks/usage_metadata 활용
2. `backend/app/core/ai/context_compression.py` 신설:
   - `compress_dataset_meta(snapshot, target_budget_chars)`: 컬럼 요약 축약, sample 값은 상위 k개만
   - `mask_pii(value)`: 이메일/전화/ID 패턴 마스킹
3. Token budget 초과 경고를 `trace_logging`에 노출

**관련 파일:**
- `backend/app/core/ai/llm_gateway.py` (전체)
- `backend/app/modules/planner/service.py` (182-216)

---

### H-3. 프롬프트 버전 관리 및 A/B 평가 불가

**현재 상태:**
- `PlannerService`의 `PROMPTS = PromptRegistry({...})` (planner/service.py:19-54)처럼 프롬프트가 Python 소스에 하드코딩됨
- `PromptRegistry`는 버전/메타데이터 없이 key-value 로딩만 수행

**문제점:**
- 프롬프트 튜닝 시 성능 회귀/개선을 정량적으로 비교 불가
- "프롬프트 엔지니어링"을 핵심 기술로 주장하려면 최소한의 버전 관리 근거 필요

**권장 수정 사항:**
1. `backend/app/core/ai/prompts/` 디렉터리 신설 — YAML로 외부화:
   ```
   prompts/
     planner/decision.system.v1.yaml
     analysis/codegen.system.v1.yaml
     analysis/repair.system.v1.yaml
   ```
2. `PromptRegistry`를 `load_prompt(key, version="active")` 형태로 확장
3. `LLMGateway._log_call`에 `prompt_version` 기록 → 벤치마크 리포트와 조인 가능

**관련 파일:**
- `backend/app/modules/planner/service.py` (19-54)
- `backend/app/core/ai/prompt_registry.py`

---

### H-4. RAG Relevance Threshold 및 품질 검증 부재

**현재 상태:**
- RAG 서브그래프에서 `top_k=3` 고정, relevance score threshold 없이 상위 3개를 무조건 반환
- `RagResultPayload` (state.py:28-37)에 `has_evidence: bool`만 있고 실제 score 정보 없음

**문제점:**
- 질문과 무관한 문서 top-3이 그대로 LLM에 전달되어 hallucination 유발
- "근거 기반 AI" 주장의 신뢰성 저하

**권장 수정 사항:**
1. `rag_service.query_for_source`에 `score_threshold: float = 0.5` 파라미터 추가 — threshold 미만 청크 제외
2. 필터링 후 0개면 `has_evidence=False` + `no_evidence_reason="below_threshold"` 세팅
3. Threshold를 `backend/app/core/config.py` 또는 환경변수로 튜닝 가능하게 노출
4. Guideline 서비스에도 동일 threshold 적용

**관련 파일:**
- `backend/app/modules/rag/service.py`
- `backend/app/orchestration/state.py` (RagResultPayload)

---

### H-5. Error Stage 분류 체계 미세분화 부재

**현재 상태:**
- 에러 분류가 "어떤 노드에서 실패했는가"(stage) 수준에 머물고, "왜 실패했는가"(cause) 차원 없음
- Repair 루프는 `analysis_error.message` 문자열만 LLM에 전달해 LLM이 원인을 추론

**문제점:**
- 동일한 `result_validation` 오류여도 "used_columns 불일치" vs "summary 누락"은 처리 전략이 달라야 하나 구분 안 됨
- 자동 분기 로직(C-1 이슈)을 구현할 때 신뢰할 분류 키 없음

**권장 수정 사항:**
1. `AnalysisError`에 `cause: Literal["column_missing","aggregation_incompatible","contract_violation","dtype_mismatch","empty_result","timeout","runtime_exception","llm_schema_violation","other"]` 필드 추가
2. `processor._validate_output_payload`가 `(cause, message)` 튜플을 반환하도록 시그니처 변경
3. `_run_code_generation_loop`에서 cause별 다음 액션 결정:
   - `column_missing` → replan (ground_columns 재수행)
   - `contract_violation` → repair (템플릿 힌트 주입)
   - `timeout` → dataset sample fallback

**관련 파일:**
- `backend/app/modules/analysis/schemas.py` (AnalysisError, ErrorStage)
- `backend/app/modules/analysis/processor.py` (400-535)
- `backend/app/modules/analysis/service.py` (425-453)

---

## [High] 프론트엔드 & 통합 이슈

### H-6. Explainable Visualization: 차트 선택 이유가 UI에 미노출

**현재 상태:**
- 백엔드 `visualization/planner.py`는 `reason` 필드를 풍부하게 생성하나 `executor.py`는 이를 `caption`에만 사용
- `DetailsPanel.tsx`와 `VisualizationResultView.tsx`는 정적 문자열만 표시, 차트 선택 근거(reason)를 렌더하지 않음

**문제점:**
- 사용자가 "왜 이 차트 타입이 선택됐는가?"를 알 수 없어 AI 의사결정이 블랙박스로 느껴짐
- 백엔드가 이미 reasoning을 생성하고 있음에도 프론트에서 버려지는 신호

**권장 수정 사항:**
- `VisualizationResultPayload`에 `planner_reason` 필드 명시적 추가
- `DetailsPanel`의 "Analysis Insights" 섹션에 "차트 선택 이유" 항목 별도 Lightbulb 아이템으로 분리
- `visualization.decision_trace` 객체(선택 컬럼 타입, 대안 차트)를 backend → state_view → 프론트로 전달
- `VisualizationResultView`에서 `reason(왜)`과 `caption(무엇)` 시각적 분리

**관련 파일:**
- `backend/app/modules/visualization/planner.py`
- `frontend/src/app/components/visualization/VisualizationResultView.tsx`
- `frontend/src/app/components/genui/DetailsPanel.tsx`

---

### H-7. Trace Chain 시각화 부재 (질문 → route → columns → code → result)

**현재 상태:**
- 프론트엔드 어디에도 `question_understanding`, `column_grounding`, `primary_evidence`, `answer_context`에 매핑되는 뷰 컴포넌트 없음
- `useAnalysisPipeline`은 `thoughtSteps`를 "메시지 목록"으로 표시할 뿐 체인으로 재구성하지 않음

**문제점:**
- 캡스톤 발표에서 "근거 기반 분석" 강점을 한눈에 증명할 UI 없음
- planner route, grounded columns, 생성된 코드, 실행 결과가 서로 다른 자료구조에 분산

**권장 수정 사항:**
- `DetailsPanel`에 신규 탭 `"Trace"` 추가 또는 별도 `TraceChainView` 컴포넌트 신설: 5단계 Step row (Question → Route → Columns → Code → Result) 각각에 근거 페이로드 바인딩
- backend `state_view`에서 `trace_chain: { question, route, grounded_columns, generated_code, result_summary, duration_ms }` 단일 객체를 SSE `done` 이벤트에 포함
- 각 단계의 `duration_ms`를 연속 막대로 시각화 (Stage latency도 함께 해결)

**관련 파일:**
- `frontend/src/app/components/genui/DetailsPanel.tsx`
- `frontend/src/app/hooks/useAnalysisPipeline.ts`
- `backend/app/orchestration/state_view.py`

---

### H-8. Stage-level Latency 대시보드 부재

**현재 상태:**
- 백엔드는 `core/trace_logging.py`, `llm_gateway.py`에서 이미 `duration_ms`를 수집
- 프론트엔드에서 `duration_ms`를 소비·집계·렌더하는 컴포넌트 없음 (총 경과 시간만 표시)

**문제점:**
- planner/analysis/rag/visualization 각 단계의 latency를 발표에서 즉석 증명 불가
- 백엔드 데이터가 이미 존재하므로 미활용 ROI 손실

**권장 수정 사항:**
- SSE `thought` 이벤트에 stage별 `started_at/ended_at/duration_ms` 일관 포함
- `StageLatencyStrip` 컴포넌트: 단계별 가로 막대 + ms 라벨
- 세션 전체 stage latency 미니 대시보드 (누적 표)

**관련 파일:**
- `backend/app/core/trace_logging.py`
- `frontend/src/app/hooks/useAnalysisPipeline.ts`
- `frontend/src/app/components/genui/PipelineBar.tsx`

---

### H-9. PII 마스킹 부재: 전체 데이터가 LLM 프롬프트로 전달

**현재 상태:**
- `run_service.py` 프롬프트 생성에 PII 필터링 단계 없음 — `dataset_context`가 raw sample을 그대로 전달
- `DetailsPanel.tsx`의 HITL 승인 카드가 `preview_rows`를 raw JSON으로 노출

**문제점:**
- 사용자 업로드 CSV의 이메일/이름/전화번호가 그대로 OpenAI API로 전송
- 화면 캡처 시 유출 위험

**권장 수정 사항:**
- 업로드 시 dataset profile 단계에서 컬럼별 PII 후보 감지 (이메일/전화/이름 regex), 결과를 `dataset_profile.pii_columns`에 저장
- LLM 프롬프트 경로에서 PII 컬럼 샘플 값을 `<redacted:email>` placeholder로 치환 (실제 값은 sandbox 실행 단계에서만 사용)
- 프론트엔드: `DetailsPanel` preview에 PII 컬럼 자동 블러/마스킹 토글

**관련 파일:**
- `backend/app/modules/analysis/run_service.py`
- `frontend/src/app/components/genui/DetailsPanel.tsx`

---

### H-10. RAG + Analysis 하이브리드 단절: RAG 도메인 지식이 Codegen에 미주입

**현재 상태:**
- 워크플로우가 `analysis | rag | preprocess` 배타적 분기 구조 — rag 결과가 analysis 코드 생성 단계로 환류되지 않음
- `run_service.py` 프롬프트에 RAG domain knowledge 주입 경로 없음

**문제점:**
- "FAISS 기반 RAG + 데이터 분석"이 실제로는 Q&A 전용, 분석 정확도 향상에 미기여
- "RAG가 왜 필요한가?"에 대한 답이 약해짐

**권장 수정 사항:**
- planner 단계에서 analysis 선택 시 RAG retrieval을 parallel 호출하여 `domain_context` 텍스트 생성
- `run_service.build_family_prompt_fragment`에 `domain_context` 섹션 삽입
- Trace chain에 "Domain Knowledge Used" step 추가, 사용된 RAG 스니펫(출처+유사도)을 인용 카드로 표시

**관련 파일:**
- `backend/app/modules/analysis/run_service.py`
- `backend/app/orchestration/builder.py`
- `frontend/src/app/components/genui/DetailsPanel.tsx`

---

### H-11. SSE 오류 처리 및 복구 취약

**현재 상태:**
- `useAnalysisPipeline.ts`의 `consumeSseResponse`는 `sse: error` 이벤트 발생 시 상태만 변경, 자동 재연결·resume token·부분 결과 보존 로직 없음 (`reconnect` 키워드 0건)
- `DetailsPanel`의 error 뷰는 하드코딩된 샘플 문구만 표시하고 실제 에러 원인과 미연동

**문제점:**
- 네트워크 단절 시 사용자가 진행 중이던 분석 결과를 모두 잃음
- HITL 승인 대기 중 SSE가 끊기면 pending approval 복구 경로 불명확

**권장 수정 사항:**
- `consumeSseResponse`에 exponential backoff 재연결(최대 3회) + resume token 전달 (기존 `/chats/{session_id}/runs/{run_id}/resume` 활용)
- `transitionToError` 시 "완료된 step"과 "실패한 step"을 partial state로 유지
- `DetailsPanel` error state를 실제 `terminalError`/`runStatus` 데이터로 치환
- Toast + 재연결 배너 UI: "연결이 끊어졌습니다. 3초 후 재시도 (1/3)..."

**관련 파일:**
- `frontend/src/app/hooks/useAnalysisPipeline.ts`
- `frontend/src/app/components/genui/DetailsPanel.tsx`
- `frontend/src/lib/api.ts`

---

### H-12. Sandbox require_print 불일치

**현재 상태:**
- `sandbox.py` 실제 실행 경로: `validate_analysis_source_code(code, require_print=False)`
- `processor.py:381`에서만 `require_print=True` 사용 → 실행 전 검증이 느슨

**문제점:**
- "엄격 통제된 sandbox"라는 주장이 발표에서 공격 포인트가 될 수 있음
- 결과 형식이 보장되지 않으면 `VisualizationResultView`의 `chart_data` 분기가 fallback으로 떨어짐

**권장 수정 사항:**
- `sandbox.py` 실행 경로를 `require_print=True`로 변경, AST 수준에서 JSON serialize 가능한 출력 강제
- 검증 실패 시 구조화된 에러(`validation_failed: missing_print`)를 SSE error 이벤트에 포함
- `DetailsPanel`/`ErrorCard`에 구조화된 사유와 재시도 버튼 함께 표시

**관련 파일:**
- `backend/app/modules/analysis/sandbox.py`
- `backend/app/modules/analysis/processor.py` (366-397)

---

### H-13. 파이프라인 상태 모델: 프론트엔드 state가 백엔드 스테이지와 1:1 매핑 안 됨

**현재 상태:**
- 백엔드 워크플로우는 9+ 단계를 가지나 프론트엔드 state는 6가지 (`empty|uploading|ready|streaming|needs-user|error`)
- 사용자가 지금 어느 백엔드 노드가 실행 중인지 알 수 없음

**문제점:**
- planner/codegen/execution 구분 불가능
- `latestVisualizationResult`가 최신 것만 유지 → 복수 결과 비교/이전 단계 회귀 불가

**권장 수정 사항:**
- 백엔드 `state_view`에서 `current_stage`, `completed_stages`, `pending_stages`를 명시적 enum으로 노출
- 프론트엔드 state에 `currentStage` 필드 추가, `PipelineBar`에 9+ 단계 고정 렌더(완료/진행/대기 3색)
- `DetailsPanel`의 artifact 타입을 discriminated union (`{ kind: "chart" | "table" | "report_draft" | "code" | "evidence"; payload }`)으로 일반화
- 여러 아티팩트를 축적하는 `artifactStack` 구조로 확장

**관련 파일:**
- `frontend/src/app/pages/Workbench.tsx`
- `frontend/src/app/hooks/useAnalysisPipeline.ts`
- `backend/app/orchestration/state_view.py`

---

## [Medium] 개선 권고

### M-1. DetailsPanel "Download PNG / View Data" 버튼 미구현

**현재 상태:** `DetailsPanel.tsx:450-455`의 버튼에 `onClick` 핸들러 없음 (placeholder 상태)

**권장 수정 사항:**
- Download PNG: `base64 → blob → URL.createObjectURL → anchor click`; Vega-Lite면 VegaEmbed view API로 PNG export
- View Data: `chart_data` 또는 `fallback_table`을 모달/side sheet에 표 렌더

---

### M-2. VisualizationResultView의 chart_type 지원 범위 한정

**현재 상태:** `VisualizationResultView.tsx`는 `line/scatter/bar` 3종만 렌더. 백엔드 planner는 `bar/line/scatter/hist/box` 5종을 계획.

**권장 수정 사항:**
- Recharts에 `hist`(BarChart + 구간화) / `box` 지원 추가
- 또는 `hist`/`box`일 때 백엔드에서 항상 `vega_lite_spec`을 생성해 VegaEmbed 경로로 처리

---

### M-3. orchestration/tools 레지스트리 성장성 부족

**현재 상태:** `tools/__init__.py`는 `build_planner_tools` 하나만 export. trace/evidence/domain tool 관례 없음.

**권장 수정 사항:**
- `orchestration/tools/`에 `trace_registry`, `evidence_registry`, `domain_context_registry` 명시적 모듈 분리
- `builder.py`가 단일 import 지점으로 tool set을 구성하도록 통일

---

## 우선순위 로드맵

```
Priority 1 — 발표 필수 (정량 증거 확보)
  ① C-3: 벤치마크 harness + routing confusion matrix
  ② C-2: Hallucination guard (수치 추출 일관성 검증 간이 버전)
  ③ H-7: Trace chain UI (question → route → columns → code → result)
  ④ H-6: Explainable Visualization reason 노출

Priority 2 — AI Agent 차별성 강화
  ⑤ C-1 + H-5: Self-reflection + Error cause 분류 통합
  ⑥ H-4: RAG relevance threshold 추가
  ⑦ H-10: RAG + Analysis 하이브리드 연결
  ⑧ H-12: Sandbox require_print=True 변경 (백엔드 1줄 + 프롬프트 정비)

Priority 3 — 운영·확장 기반
  ⑨ H-8: Stage latency 대시보드 (백엔드 데이터 이미 존재, ROI 최고)
  ⑩ H-11: SSE 에러 복구 (exponential backoff + resume token)
  ⑪ H-9 + H-2: PII 마스킹 + Token/Context 관리
  ⑫ H-1: Codegen Strategy Fallback (Python ↔ SQL)
  ⑬ H-3: 프롬프트 버전 관리 외부화
  ⑭ H-13: 파이프라인 state 통합
  ⑮ M-1~M-3: Medium 이슈들
```

---

## Open Questions

| # | 질문 | 관련 이슈 |
|---|------|-----------|
| Q1 | `max_retries=1`의 LLM 호출 예산이 얼마나 증가해도 허용 가능한가? critique 루프 도입 시 상한 결정에 필요 | C-1 |
| Q2 | Hallucination guard에서 허용 오차(수치 일치 범위, LLM judge threshold)를 몇으로 둘 것인가? | C-2 |
| Q3 | 벤치마크 테스트셋 ground truth를 누가 작성·검수하는가? | C-3 |
| Q4 | 프롬프트 외부화 시 기존 `PromptRegistry`를 확장할지 새 레지스트리로 교체할지? | H-3 |
| Q5 | RAG score threshold 기본값과 embedding 모델의 정규화 방식은? | H-4 |
| Q6 | PII 마스킹 기본값 — LLM raw 값 전송 opt-in vs masked 기본에 unmask 토글? | H-9 |
| Q7 | Trace chain 단계 수 — 5단계 고정 vs `completed_stages` 배열에 따라 동적 확장? | H-7 |
| Q8 | SSE 재연결 시 `/resume` 엔드포인트가 "approve/revise/cancel" 결정용인지 "끊긴 스트림 재개용"으로 겸용 가능한지? | H-11 |
| Q9 | Sandbox `require_print=True`로 변경 시 기존 통과 테스트셋/프롬프트 회귀 영향 범위 사전 측정 필요 | H-12 |
| Q10 | RAG snippet을 codegen에 주입할 때 토큰 예산 초과 대응 전략은? (H-2와 결합) | H-10 |

---

*이 문서는 AI 에이전트(백엔드 분석 + 프론트엔드/통합 분석)의 병렬 코드 분석 결과를 통합한 것입니다.*  
*변경 사항 반영 시 이 파일을 업데이트하고 관련 AI 에이전트들과 공유하세요.*
