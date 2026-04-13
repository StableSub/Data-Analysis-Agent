# 캡스톤 발표 준비 분석 — AI 로직 관점

> Claude(Opus 4.6) + Codex(GPT) + Gemini 3-model Cross-Verification 결과  
> 작성일: 2026-04-12

---

## 1. 캡스톤 발표 구성 요소

컴퓨터학부 졸업 캡스톤 발표는 일반적으로 다음 구조를 따릅니다.

| 섹션 | 내용 |
|------|------|
| **문제 정의 & 동기** | 기존 데이터 분석 툴의 한계, 왜 이 프로젝트가 필요한가 |
| **관련 연구 / 기존 시스템 비교** | ChatGPT Code Interpreter, Julius AI, Pandas AI 등과 차별점 |
| **시스템 아키텍처** | 전체 구조도, 기술 스택, 데이터 흐름 |
| **핵심 기술 / 알고리즘** | AI Agent 설계, 프롬프트 엔지니어링, 워크플로우 라우팅 로직 |
| **구현 상세** | 주요 모듈별 구현, 코드 생성/실행 파이프라인 |
| **실험 / 평가** | 정량적 성능 지표, 정확도 평가, 사용자 테스트 |
| **데모** | 실제 동작 시연 (4가지 시나리오 권장) |
| **한계점 & 향후 계획** | 개선 방향 |

### 권장 데모 시나리오 (4가지)

1. 일반 질문 (general_question 경로)
2. 분석 질문 (analysis 경로 — 코드 생성·실행·결과)
3. RAG 질문 (retrieval_qa 경로)
4. 실패 / clarification 사례 (self-healing 또는 명확화 요청)

### 평가 기준 (일반적 캡스톤)

- **창의성 · 기획성** — 문제 정의의 참신성
- **기술성 · 완성도** — 구현 깊이와 안정성
- **실사용 가능성** — 실제 동작하는 소프트웨어 시연
- **발표력** — 논리적 전달, 질의응답 대응

---

## 2. 프로젝트 현황 요약

### 강점

- LangGraph StateGraph 기반의 역할 분리된 AI 파이프라인
  - `PlannerService`: 라우팅 + 질문 구조화 분리
  - `AnalysisService`: 계획 수립 → 코드 생성 → 실행 → 복구 루프
  - RAG / Visualization / Report 독립 서브그래프
- Evidence packaging (`answer_context`) — 근거 기반 최종 답변 조립
- Sandbox 실행 격리 + AST 기반 금지 호출 차단
- SSE 기반 실시간 thought step 스트리밍

### AI 워크플로우

```
intake_flow
└─ dataset 선택
   → dataset_context → guideline_flow → planner
      → analysis | rag | preprocess | dataset_lookup
         → visualization (optional)
         → merge_context → data_qa_terminal
         → report (optional)
```

---

## 3. AI 로직 관점 부족 사항 (3-model 합의)

### 3.1 [Critical] 정량적 평가 체계 부재

**현황**
- 단위 테스트(`test_planner_analysis_accuracy_guards.py` 등)는 있으나 제품 수준 벤치마크 없음
- 라우팅 정확도, column grounding 정확도, 최종 답변 정확도, code repair 성공률 지표 없음

**보완 방향**
- 20~30개 테스트 질문셋 구축 → routing confusion matrix 작성
- 10~15개 분석 질문의 ground truth 표 → answer accuracy & repair success rate 측정

> 발표에서 "구조는 좋은데 실제로 얼마나 잘 되는가?" 질문에 답할 수 없으면 치명적.

---

### 3.2 [Critical] Self-reflection / 자기 검증 부족

**현황**
```python
# service.py
for attempt in range(self.max_retries + 1):  # max_retries=1
    ...
    generated_code = self.run_service.repair_analysis_code(...)
```
- 코드 수정 재시도만 있고, 에러 원인을 구조적으로 분석하는 Critique 단계 없음
- Plan 자체를 수정하는 adaptive planning 없음

**보완 방향**
- 실패 원인 분류 노드 추가 (column_error / logic_error / timeout 등)
- 원인에 따라 plan 수정 vs. code repair 분기
- ReAct 패턴 또는 Chain-of-Thought 기반 자기 검증 도입

---

### 3.3 [High] Sandbox 신뢰성 설명 부족

**현황**
```python
# sandbox.py
validate_analysis_source_code(code, require_print=False)  # require_print가 False
```
- AST 기반 금지 호출/모듈 차단은 있으나 `require_print=False`로 출력 강제 검사 없음
- "엄격하게 통제된 실행"이라고 주장하기에 약간 모순

**보완 방향**
- 발표에서는 제한사항을 솔직하게 설명
- 또는 `require_print=True`로 변경하여 JSON 출력을 강제 검증

---

### 3.4 [High] RAG 품질 관리 미흡

**현황**
```python
# rag workflow
retrieved = rag_service.query_for_source(query=query, top_k=3, ...)
```
- top_k=3 고정, relevance threshold 없이 무조건 상위 3개 반환
- hit-rate / retrieval quality benchmark 없음

**보완 방향**
- relevance score threshold 추가 (예: score < 0.5이면 no_evidence 처리)
- RAG 질문 전용 테스트셋으로 hit-rate 측정

---

### 3.5 [High] 근거 추적 시각화 부재

**현황**
- `answer_context`에 `question_understanding`, `column_grounding`, `primary_evidence` 포함
- 발표용 한눈에 보이는 trace 체인 없음

**보완 방향**
- 발표 슬라이드: 질문 → route → grounded columns → metric → answer 한 장 시각화
- `trace_logging`의 `duration_ms` 데이터를 stage별 p50/p95로 집계

---

## 4. 모델별 고유 인사이트

### Codex (GPT) — 발표 전략 중심

- Stage별 latency 대시보드 필수 (`LLMGateway`의 `duration_ms`를 집계하면 바로 가능)
- Trace 시각화 슬라이드: question → route → grounded columns → metric → answer
- Confusion matrix로 planner routing 정확도 증명

### Gemini — 시스템 안전성·통합 중심

- **PII 마스킹**: 현재 전체 데이터를 LLM 프롬프트에 전달 → 실제 값 대신 메타데이터만 전달하는 전략 검토
- **RAG + Analysis 하이브리드**: RAG에서 얻은 도메인 지식을 코드 생성에 반영하는 시나리오 부재
- **Explainable Visualization**: AI가 특정 차트 타입을 선택한 이유(reasoning)를 사용자에게 전달

### Claude (Lead) — AI 로직 깊이 중심

- **Hallucination Guard**: summary ↔ raw_metrics/table 간 의미적 일관성 cross-check 없음
- **Codegen Strategy Fallback**: Python 실패 시 SQL 전환 등 전략 간 fallback 없음
- **Token/Context 관리**: `LLMGateway`에 토큰 사용량 추적·프롬프트 압축 전략 없어 대용량 dataset 취약
- **프롬프트 버전 관리**: 모든 프롬프트가 Python 문자열 하드코딩 → A/B 테스트·성능 비교 불가

---

## 5. 발표 전 우선순위 로드맵

```
Priority 1 — 발표 필수 (정량 증거 확보)
  ① 20~30개 테스트 질문셋 + routing confusion matrix
  ② 10~15개 분석 질문의 ground truth → 실행 성공률·결과 정확도
  ③ Trace 시각화 슬라이드 (question → route → columns → code → result)

Priority 2 — AI Agent 차별성 강화
  ④ Self-reflection 노드: 실패 원인 분류 → plan 수정 or code repair 분기
  ⑤ Hallucination guard: summary ↔ raw_metrics 일관성 검증
  ⑥ RAG relevance threshold 추가

Priority 3 — Nice-to-have
  ⑦ Stage별 latency 계측 대시보드
  ⑧ Explainable Visualization (차트 선택 이유 제공)
  ⑨ PII 마스킹 / Token 관리 전략
```

---

## 6. 핵심 메시지

> 현재 프로젝트는 **워크플로우 설계와 구현 완성도가 높지만**,  
> 캡스톤에서 가장 중요한 **"그래서 얼마나 잘 되는가?"에 대한 정량적 증거**가 없습니다.  
>
> "단순히 LLM 연결이 아닌, 역할 분리된 파이프라인"이라는 강점을 살리면서  
> **테스트셋 기반 평가 결과 확보**가 발표 성패를 좌우합니다.
