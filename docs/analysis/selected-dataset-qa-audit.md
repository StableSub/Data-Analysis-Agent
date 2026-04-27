# 선택 데이터셋 QA 감사

## 문서 목적

이 문서는 **현재 브랜치의 실제 코드**를 기준으로, 사용자가 데이터셋을 선택한 뒤 질문했을 때 백엔드 로직에서 정확성을 떨어뜨릴 수 있는 지점을 정리한다. 특히 `데이터 선택 -> 질문 해석 -> 분석/RAG -> 최종 답변` 흐름이 **데이터 분석 AI Agent Flow**로서 어디가 부족한지에 집중한다.

이 문서는 개선안을 설계하기 위한 감사 문서다. 현재 동작을 미화하지 않고, 실제 런타임과 그 한계를 그대로 기록한다.

## 감사 범위

- 실행 진입점: `backend/app/modules/chat/service.py`, `backend/app/orchestration/client.py`
- 메인 분기: `backend/app/orchestration/builder.py`, `backend/app/orchestration/intake_router.py`
- 분석 경로: `backend/app/orchestration/workflows/analysis.py`, `backend/app/modules/analysis/service.py`, `backend/app/modules/analysis/run_service.py`, `backend/app/modules/analysis/processor.py`
- RAG/지침 경로: `backend/app/orchestration/workflows/rag.py`, `backend/app/orchestration/workflows/guideline.py`, `backend/app/modules/rag/service.py`, `backend/app/modules/rag/ai.py`
- 데이터셋/프로파일링: `backend/app/modules/datasets/service.py`, `backend/app/modules/profiling/service.py`
- 관련 문서/테스트 드리프트 확인: `docs/architecture/**/*.md`, `backend/tests/test_architecture_docs.py`

## 현재 브랜치의 실제 실행 흐름

현재 메인 워크플로우의 실제 분기는 `backend/app/orchestration/builder.py` 기준으로 아래에 가깝다.

```text
selected dataset request
-> intake_flow
-> preprocess_flow
-> analysis_flow 또는 rag_flow
-> guideline_flow(optional, after analysis/rag)
-> visualization_flow(optional)
-> merge_context
-> data_qa_terminal 또는 report_flow
```

여기서 중요한 점은 다음과 같다.

- `builder.py`에는 `dataset_context` node가 없다.
- `builder.py`에는 `planner` node가 없다.
- `builder.py`에는 `dataset_lookup_terminal`이 없다.
- `state.py`에는 문서에서 설명하는 `planning_result`, `dataset_context`, `answer_context` 필드가 없다.
- 과거 architecture 문서 일부는 현재 런타임보다 더 진보된 planner 중심 구조를 설명하고 있었다.

즉, 현재 브랜치는 **문서상 planner 중심 구조가 아니라, intake에서 coarse intent를 만든 뒤 preprocess/analysis/rag로 바로 들어가는 구조**다.

## 핵심 문제점

### 1. 선택 데이터셋 질문에도 planner 기반 정밀 분기가 없다

가장 큰 문제는 현재 selected-dataset 질문 흐름에 문서화된 planner 계층이 실제로 존재하지 않는다는 점이다.

- `backend/app/orchestration/intake_router.py`
  - `source_id`가 있으면 무조건 `analyze_intent`를 거쳐 `handoff.next_step = "data_pipeline"`으로 보낸다.
- `backend/app/orchestration/ai.py`
  - `intent.system` 프롬프트가 "데이터셋이 이미 선택된 상황이다. step은 data_pipeline으로 반환하라"고 강제한다.
- `backend/app/orchestration/builder.py`
  - `intake_flow` 이후 `data_pipeline`은 바로 `preprocess_flow`로 연결된다.

이 구조에서는 질문을 `dataset_lookup`, `retrieval_qa`, `analysis`, `general_question`, `clarification`으로 세밀하게 분류하는 중간 계층이 없다. 그 결과:

- 구조 질문도 deterministic lookup 대신 RAG 또는 analysis로 흘러갈 수 있다.
- 일반 질문도 dataset이 선택되어 있다는 이유만으로 데이터 파이프라인에 들어간다.
- "어떤 방식으로 답해야 가장 정확한가"보다 "대략 분석/전처리/시각화가 필요한가" 수준의 coarse flag에 의존한다.

정확성 관점에서 이는 **질문 유형과 실행 방식의 매칭 정밀도가 낮다**는 뜻이다.

### 2. dataset lookup 전용 deterministic 경로가 없어 구조 질문 정확도가 불안정하다

문서에는 `dataset_lookup_terminal`이 있는 것으로 설명되어 있지만, 실제 구현에는 해당 terminal이 없다.

- `backend/app/orchestration/builder.py`
  - 등록된 terminal은 `general_question_terminal`, `clarification_terminal`, `data_qa_terminal`뿐이다.
- `backend/app/orchestration/intake_router.py`
  - `dataset_lookup`와 같은 route 개념 자체가 없다.

이 문제는 사용자가 아래 같은 질문을 할 때 특히 치명적이다.

- "이 데이터셋에 컬럼이 몇 개야?"
- "결측치 많은 컬럼이 뭐야?"
- "샘플 5행 보여줘"
- "날짜 컬럼이 있어?"

이런 질문은 본질적으로 deterministic 응답이 적합한데, 현재 흐름에서는 RAG 또는 analysis 계층으로 우회될 가능성이 높다. 그러면:

- 실제 프로파일 값 대신 생성형 요약이 나올 수 있고
- 컬럼 수/결측치/자료형 같은 값이 정확히 고정되지 않으며
- 데이터셋 구조 질문에 불필요한 LLM 오차가 들어간다.

### 3. 최종 답변 단계에 evidence gating과 abstain contract가 없다

문서는 `answer_context`, `primary_evidence`, `secondary_evidence`, `abstain_reason` 같은 답변 전용 패키지가 있다고 설명하지만, 현재 코드에는 없다.

- `backend/app/orchestration/builder.py`
  - `data_qa_terminal`은 `merged_context`를 그대로 `answer_data_question(...)`에 넘긴다.
- `backend/app/orchestration/ai.py`
  - `answer_data_question` 프롬프트는 "주어진 merged_context만 근거로 답하라" 수준이다.
- `backend/app/orchestration/state.py`
  - `answer_context` 필드가 없다.
- `backend/app/orchestration/state_view.py`
  - 문서와 달리 파일 자체가 존재하지 않는다.

문제는 `merged_context`가 **답변용으로 정제된 근거 계약**이 아니라는 점이다. 여러 중간 산출물이 섞인 누적 컨텍스트일 뿐이다. 따라서 최종 답변 모델은 다음을 강제받지 않는다.

- 어떤 근거가 1차 근거인지
- 근거가 부족할 때 언제 답을 멈춰야 하는지
- 분석 결과와 RAG 결과가 충돌할 때 무엇을 우선해야 하는지
- 선택된 데이터셋 범위를 벗어나는 일반화를 금지해야 하는지

즉, 현재 최종 답변은 **evidence-packaged answering**이 아니라 **merged JSON summarization**에 더 가깝다.

### 4. 선택한 데이터셋의 유효성이 너무 늦게 검증된다

현재 intake 단계는 `source_id`의 **문자열 존재 여부만** 확인한다.

- `backend/app/orchestration/intake_router.py`
  - `bool(str(state.get("source_id") or "").strip())`만 본다.
- 실제 데이터셋 존재 여부는 이후 단계에서야 확인된다.
  - analysis: `backend/app/orchestration/workflows/analysis.py`
  - rag: `backend/app/modules/rag/service.py`

이 구조에서는 아래와 같은 문제가 생길 수 있다.

- 프런트가 오래된 `source_id`를 보냈는데도 intake는 정상 흐름으로 통과시킨다.
- 삭제된 데이터셋이어도 일단 데이터 파이프라인으로 들어간다.
- 실패가 늦게 발생해 사용자 입장에서는 "선택은 됐는데 왜 갑자기 실패하지?" 같은 경험이 생긴다.

정확성뿐 아니라 **dataset binding 신뢰성** 측면에서도 약한 구조다.

추가로, 세션-데이터셋 연결을 위한 모델은 있지만 실제 질문 런타임에서 적극적으로 쓰이지 않는다.

- `backend/app/modules/datasets/models.py`
  - `SessionSource` 모델이 존재한다.
- 하지만 현재 확인한 질문 실행 경로(`chat/service.py` -> `orchestration/client.py`)에서는 세션별 데이터셋 binding을 이 모델로 재검증하지 않는다.

즉, 현재 바인딩은 **세션에 저장된 선택 상태**보다 **요청마다 넘어오는 `source_id`와 후속 state**에 더 의존한다.

### 5. analysis의 dataset metadata는 전체 데이터셋이 아니라 샘플 2,000행에 크게 의존한다

분석 계획의 핵심 입력인 metadata가 전체 데이터셋이 아니라 샘플 기반으로 만들어진다.

- `backend/app/modules/analysis/service.py`
  - `build_dataset_metadata()`가 `read_csv(..., nrows=2000)`로 샘플만 읽는다.
  - `row_count`도 실제 전체 행 수가 아니라 `len(sample_df)`다.

반면 `backend/app/modules/profiling/service.py`는 chunk 단위로 전체 missing statistics를 계산할 수 있다. 즉, 더 풍부한 데이터셋 컨텍스트 계층이 이미 있는데, analysis planning은 이를 충분히 활용하지 않는다.

이 때문에 대용량 데이터셋에서는 다음 오차가 생길 수 있다.

- 초반 2,000행에는 없지만 뒤쪽에 존재하는 값 분포를 놓친다.
- datetime 컬럼 추론이 샘플 편향을 받는다.
- group key / identifier / boolean 같은 논리 타입 정보를 analysis planning이 활용하지 못한다.
- 실제 전체 행 수 기반 질문에서 잘못된 직관으로 계획이 세워질 수 있다.

즉, 지금 planning은 **full-profile-aware**가 아니라 **sample-snapshot-aware**에 머물러 있다.

### 6. guideline은 초기 계획 품질을 높이는 입력이 아니라 뒤늦은 보조 단계다

문서에서는 guideline이 planner 이전 컨텍스트로 설명되지만, 실제 메인 그래프에서는 그렇지 않다.

- `backend/app/orchestration/builder.py`
  - guideline은 `route_after_analysis` 또는 `route_after_rag`에서 `ask_guideline`이 켜졌을 때만 실행된다.
- `backend/app/orchestration/intake_router.py`
  - 질문 분기는 guideline evidence 없이 먼저 결정된다.
- `backend/app/orchestration/workflows/analysis.py`
  - analysis planning은 `question`, `dataset_meta`, `column_grounding`만으로 진행된다.

이 말은 곧:

- guideline이 질문 해석이나 route 결정의 입력이 되지 못하고
- 잘못된 실행 경로를 초기에 막아 주지 못하며
- 최종 답변 직전의 보조 evidence로만 남을 수 있다는 뜻이다.

정확성 측면에서는 guideline이 **policy/constraint first**가 아니라 **after-the-fact context**에 가깝다.

### 7. RAG는 표 데이터 질문에 대해 row/column 수준 provenance가 부족하다

현재 RAG는 선택 데이터셋 파일을 텍스트로 읽어 chunking하고, 벡터 검색 후 짧은 insight를 합성한다.

- `backend/app/modules/rag/service.py`
  - CSV도 텍스트 파일처럼 읽어서 `_chunk_text()`로 자른다.
- `backend/app/orchestration/workflows/rag.py`
  - 검색 결과는 `retrieved_chunks`, `context`, `retrieved_count` 정도로 정리된다.
- `backend/app/modules/rag/ai.py`
  - `synthesize_insight()`는 검색 컨텍스트를 읽고 요약만 만든다.

이 방식은 문서형 RAG에는 맞을 수 있지만, 표 데이터 질문에는 한계가 명확하다.

- 특정 수치가 어느 행/조건/집계에서 나왔는지 provenance가 약하다.
- 숫자 질문이 텍스트 chunk 유사도에 과도하게 의존한다.
- 컬럼/행/집계 단위의 deterministic trace가 없다.
- retrieved chunk가 있어도 그것이 실제 정답 계산 근거라는 보장이 없다.

게다가 검색 품질 하한선도 약하다.

- `backend/app/orchestration/workflows/rag.py`
  - `top_k=3`으로 고정된 검색을 수행한다.
- `backend/app/modules/rag/service.py`
  - score threshold나 minimum evidence gate 없이 상위 결과를 그대로 사용한다.

즉, 현재 RAG는 **근거가 충분해서 답한다**보다 **검색 결과가 조금이라도 있으면 요약한다**에 더 가깝다.

즉, 현재 RAG는 **table-grounded QA**보다 **textual retrieval summary**에 더 가깝다.

### 8. 업로드/선택 가능 파일과 실제 분석 가능 파일의 계약이 불명확하다

사용자 경험상 데이터셋 업로드는 범용 파일 업로드처럼 보이지만, 실제 분석/프로파일링/전처리는 CSV 리더에 강하게 묶여 있다.

- `backend/app/modules/datasets/router.py`
  - 파일 확장자 검증 없이 업로드를 받는다.
- `backend/app/modules/datasets/service.py`
  - `DatasetReader.read_csv()`만 제공한다.
- `backend/app/modules/analysis/service.py`
  - metadata 구축 시 CSV로 읽는다.
- `backend/app/modules/preprocess/service.py`
  - 전처리도 CSV로 읽는다.
- `backend/app/modules/profiling/service.py`
  - 프로파일링도 CSV 기반이다.

반면 README는 CSV/Excel 등 다양한 표 형식을 지원한다고 설명한다. 현재 코드 기준으로는 이 계약이 강하지 않다.

이 상태에서는 사용자가 파일 업로드에는 성공했더라도, 선택 후 질문 단계에서:

- profiling 실패
- analysis 실패
- preprocess 실패
- RAG와 analysis의 capability 불일치

같은 문제가 발생할 수 있다. 정확성 이전에 **supported dataset contract** 자체가 불명확하다.

### 9. selected-dataset 질문은 항상 preprocess_flow를 먼저 통과해 불필요한 복잡성을 가진다

실제 메인 그래프는 selected-dataset request를 항상 `preprocess_flow`로 먼저 보낸다.

- `backend/app/orchestration/builder.py`
  - `data_pipeline -> preprocess_flow`

물론 preprocess 내부에서 skip될 수 있지만, 구조상 모든 selected-dataset 질문이 전처리 판단을 먼저 거친다. 이는 다음 문제로 이어진다.

- 데이터 구조 질문에도 preprocess decision이 개입한다.
- 질문 해석과 실행 전략 결정이 분리되지 않고 섞인다.
- "분석이 필요한가"와 "전처리가 필요한가"를 독립적으로 정밀 판단하기 어렵다.

지금 구조는 planner가 없기 때문에 preprocess가 사실상 **첫 번째 정책 분기기 역할을 일부 떠안고 있다**.

### 10. 정확성 회귀를 막는 테스트가 부족하다

현재 확인된 테스트는 문서 존재 검사, dataset context service, guideline workflow, report fallback, visualization path 정도다.

- `backend/tests/test_architecture_docs.py`
  - 실제 코드 존재 여부보다 문서 문자열 포함 여부를 검사하는 비중이 크다.
- `backend/tests/test_dataset_context_service.py`
  - 프로파일링 레이어는 검증하지만 메인 workflow 연결은 검증하지 않는다.
- 현재 브랜치에는 selected-dataset 질문이 어떤 경로로 흘러가는지, 언제 RAG 대신 analysis를 택해야 하는지, 최종 답변이 근거 부족 시 abstain해야 하는지 검증하는 테스트가 보이지 않는다.

그 결과 다음 종류의 회귀가 쉽게 숨어들 수 있다.

- coarse intent 변경으로 route 품질 저하
- selected dataset 질문이 잘못된 하위 경로로 이동
- merged_context 구조 변경으로 최종 답변 품질 하락
- profiling과 analysis 메타정보의 불일치

특히 현재 확인된 테스트 구성만으로는 다음을 막기 어렵다.

- 최종 `data_qa` 응답이 근거 없이도 생성되는 회귀
- 잘못된 `source_id` 또는 stale state가 다른 데이터셋으로 흘러가는 회귀
- positive guideline evidence가 실제 route/planning 품질에 반영되지 않는 회귀

## 추가 위험: stale state가 원래 선택 데이터셋보다 우선될 수 있다

현재 downstream source resolution은 원래 요청의 `source_id`보다 이전 단계 결과를 우선한다.

- `backend/app/orchestration/utils.py`
  - `resolve_target_source_id()`는 `preprocess_result.output_source_id`를 먼저 보고,
  - 그 다음 `rag_result.source_id`를 보고,
  - 마지막에야 원래 `state.source_id`를 본다.

preprocess 후속 흐름에는 이 우선순위가 필요할 수 있지만, resumed run이나 상태 재사용이 섞이면 **사용자가 현재 선택했다고 믿는 데이터셋과 실제 downstream 대상이 어긋날 위험**이 있다. 이 함수는 편의상 일관된 target source를 주지만, 동시에 **stale shared state contamination**의 중심 지점이기도 하다.

정확성 문제는 눈에 띄는 500 에러보다 더 늦게 발견되므로, 이 영역의 테스트 부재는 리스크가 크다.

## 문서와 실제 런타임의 드리프트

현재 `docs/architecture/`는 planner-centric 구조를 넓게 설명하지만, 실제 코드는 그렇지 않다. 대표적인 차이는 아래와 같다.

- 문서에는 `planner`, `dataset_context`, `dataset_lookup_terminal`, `answer_context`, `state_view.py`가 중심 요소로 나온다.
- 실제 코드에는 위 요소들이 없거나, 다른 위치/다른 계약으로 대체되어 있다.
- `backend/tests/test_architecture_docs.py`는 `backend/app/modules/planner/service.py` 같은 **실제로 존재하지 않는 구현 경로 문자열**까지 기대한다.

이 드리프트는 단순 문서 문제를 넘어, 팀이 현재 시스템의 정확성 한계를 잘못 이해하게 만든다. 즉 **운영 위험을 숨기는 문서 부채**다.

## 우선순위가 높은 개선 과제

### P0

1. selected-dataset 질문에 대한 실제 planner 계층 복원
   - 최소한 `dataset_lookup`, `retrieval_qa`, `analysis`, `clarification`, `general_question` 분리를 복구해야 한다.
2. final answer 전용 evidence contract 도입
   - `merged_context`와 별개로 `answer_context`, `dataset_scope`, `abstain_reason` 같은 패키지가 필요하다.
3. intake 단계에서 `source_id` 유효성 조기 검증
   - 존재하지 않는 데이터셋은 data pipeline 진입 전에 걸러야 한다.

### P1

1. analysis planning을 sample metadata가 아니라 full profile/dataset context 기반으로 재구성
2. dataset structure 질문용 deterministic terminal 복구
3. guideline을 후행 보조가 아니라 초기 route/planning 입력으로 승격

### P2

1. 표 데이터용 RAG provenance 강화
   - row/column/condition/aggregation trace가 필요하다.
2. 업로드 가능 포맷과 실제 분석 가능 포맷 계약 명시 및 정합화
3. accuracy regression test 추가

## 바로 확인해야 할 질문

이 브랜치에서 아래 질문에 코드 기준 답을 만들 수 있어야 한다.

- 사용자가 선택한 `source_id`가 실제로 어느 단계까지 유지되는가?
- 구조 질문은 deterministic path로 가는가, 아니면 생성형 path로 가는가?
- 최종 답변이 데이터 근거 부족 시 멈추는가?
- analysis와 RAG가 충돌하면 무엇이 더 신뢰되는가?
- full dataset profile과 analysis planning metadata가 왜 분리되어 있는가?

현재 코드 기준으로는 이 질문들에 대한 답이 충분히 강하지 않다.

## 결론

현재 브랜치의 백엔드 Agent Flow는 "선택된 데이터셋 기반 질문에 대해 정확한 실행 경로를 먼저 고른 뒤, 근거를 패키징해 답변한다"기보다, **coarse intent로 빠르게 하위 플로우를 태우고 마지막에 merged context를 요약하는 구조**에 더 가깝다.

따라서 가장 큰 리스크는 단순 실패가 아니라 다음 세 가지다.

1. **잘못된 경로 선택**
2. **부족한 dataset grounding**
3. **근거 패키징 없이 생성되는 최종 답변**

선택 데이터셋 기반 QA의 정확도를 높이려면, planner 복원과 answer-context 계약 복원이 가장 먼저 필요하다.
