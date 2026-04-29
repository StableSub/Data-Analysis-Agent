# Analysis module

`backend/app/modules/analysis/`는 자연어 데이터 질문을 구조화된 분석 계획으로 바꾸고, pandas 실행 코드를 생성·검증·sandbox 실행한 뒤 `backend/app/modules/results/`에 저장하는 핵심 AI 분석 module이다. orchestration에서는 `backend/app/orchestration/workflows/analysis.py`가 이 module을 호출한다.

## 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/analysis/__init__.py` | analysis package marker다. |
| `backend/app/modules/analysis/dependencies.py` | `AnalysisProcessor`, `AnalysisRunService`, `AnalysisSandbox`, `ResultsRepository`, `AnalysisService`를 FastAPI dependency/builder 형태로 조립한다. |
| `backend/app/modules/analysis/processor.py` | 컬럼 grounding, plan 검증, 생성 코드 AST 검증, 실행 결과 payload 검증, error object 생성을 담당하는 deterministic rule engine이다. |
| `backend/app/modules/analysis/router.py` | `APIRouter(prefix="/analysis")`로 `POST /analysis/run`, `GET /analysis/results/{analysis_result_id}`를 제공한다. |
| `backend/app/modules/analysis/run_service.py` | LLM 기반 질문 이해, 분석 계획 초안, 코드 생성, repair instruction 생성, JSON/code fence normalization을 담당한다. |
| `backend/app/modules/analysis/sandbox.py` | 생성된 Python 코드를 별도 script 형태로 실행하고 stdout/stderr/result JSON을 수집한다. |
| `backend/app/modules/analysis/schemas.py` | 분석 계획·검증·실행 결과·error stage/status에 쓰이는 Pydantic 계약을 정의한다. |
| `backend/app/modules/analysis/service.py` | dataset metadata 수집부터 plan/code generation loop, sandbox 실행, 결과 저장, visualization output 생성까지 analysis use case를 조립한다. |

## Runtime 입력과 출력

- 입력 state/API 값:
  - `user_input`: 자연어 질문.
  - `source_id`: 선택된 dataset source id.
  - `model_id`: LLM 호출 model id.
  - `session_id`: 저장 결과와 연결되는 session id.
- 주요 중간 산출물:
  - `dataset_meta`, `question_understanding`, `column_grounding`, `analysis_plan_draft`, `analysis_plan`.
  - `generated_code`, `validated_code`, `sandbox_result`, `analysis_error`, `retry_count`, `final_status`.
- 주요 출력:
  - `analysis_result`: `AnalysisExecutionResult` 계열 결과.
  - `analysis_result_id`: `ResultsRepository`에 저장된 id.
  - `output`: 실패/clarification 등 terminal content가 필요한 경우 orchestration에서 사용된다.

## Hotspot: `backend/app/modules/analysis/service.py`

### 역할

`AnalysisService`는 analysis module의 application service다. LLM step과 deterministic validation, sandbox 실행, DB 저장을 한 use case로 연결한다.

### 주요 method

- `build_dataset_metadata(source_id)`: dataset repository/reader로 파일과 컬럼 metadata를 읽어 `MetadataSnapshot`을 만든다.
- `run(...)`: public API `POST /analysis/run`에서 쓰이는 단일 실행 entrypoint다.
- `_run_code_generation_loop(...)`: 코드 생성, AST 검증, sandbox 실행, 결과 검증, repair 반복을 담당한다.
- `_build_clarification_response(...)`: 질문/plan ambiguity가 남을 때 clarification 응답을 만든다.
- `_build_visualization_output(...)`: analysis 결과를 visualization module이 이해할 수 있는 output 구조로 정리한다.
- `_persist_result(...)`: `ResultsRepository`에 analysis result와 chart/view snapshot을 저장한다.

### 연결 관계

- `backend/app/modules/analysis/dependencies.py`가 repository/reader/processor/run_service/sandbox와 함께 `AnalysisService`를 만든다.
- `backend/app/orchestration/workflows/analysis.py`가 planning/execution/validation/persist node에서 이 service를 호출한다.
- `backend/app/modules/visualization/service.py`는 analysis result 기반 chart 생성을 위해 analysis output 구조를 소비한다.
- `backend/app/modules/results/repository.py`는 저장된 결과를 `/analysis/results/{analysis_result_id}`와 `/export/csv`에서 재사용하게 한다.

### 주의점

- AI가 만든 plan/code를 바로 실행하지 않고 `AnalysisProcessor`와 `AnalysisSandbox`를 거친다.
- `final_status`가 `needs_clarification`, `fail`, `success` 중 무엇인지에 따라 main workflow terminal route가 달라진다.
- code generation loop의 retry 판단은 module 내부 책임이고, main workflow는 최종 state만 보고 다음 subgraph를 선택한다.

## Hotspot: `backend/app/modules/analysis/processor.py`

### 역할

`AnalysisProcessor`는 LLM 결과를 runtime에서 실행 가능한 안전한 형태로 좁히는 deterministic 검증 계층이다.

### 주요 책임

- `ground_columns(...)`: 질문 이해 결과와 dataset metadata를 대조해 사용할 컬럼을 확정한다.
- `validate_and_finalize_plan(...)`: plan draft를 실제 분석 계획으로 검증·정리한다.
- `validate_generated_code(...)`: 생성 코드의 import/call/output 계약을 검사한다.
- `validate_execution_result(...)`: sandbox result가 expected output 계약을 만족하는지 확인한다.
- `normalize_empty_result(...)`: 빈 결과를 frontend/answer 계층이 다룰 수 있는 형태로 정리한다.
- `build_error(...)`: `AnalysisError` payload를 만든다.

### 주요 상수

- `_ALLOWED_IMPORT_ROOTS`: 생성 코드 import allowlist.
- `_FORBIDDEN_CALLS`: 생성 코드에서 금지되는 call 패턴.
- `_OUTPUT_KEYS`: sandbox result에서 허용되는 output key.
- `_TIME_AXIS_BY_GRAIN`: 시간 grain별 axis 처리 기준.

### 주의점

- 이 파일은 analysis 정확도와 안전성에 직접 연결된다.
- 질문 해석/plan 생성 prompt를 바꿀 때도 이 processor가 요구하는 schema와 output key를 같이 확인해야 한다.

## Hotspot: `backend/app/modules/analysis/run_service.py`

### 역할

`AnalysisRunService`는 LLM을 호출해 질문 이해, plan draft, 코드 생성, 코드 repair를 수행한다.

### 주요 책임

- 질문에서 metric, dimension, filter, time context, ambiguity를 추출한다.
- grounded columns와 metadata를 받아 `AnalysisPlanDraft`를 만든다.
- plan과 이전 error를 근거로 pandas code를 생성하거나 repair한다.
- LLM 응답에서 JSON/code fence를 제거하고 schema validation으로 넘긴다.

### 연결 관계

- `backend/app/core/ai/llm_gateway.py`의 `LLMGateway`와 `PromptRegistry`를 사용한다.
- `AnalysisProcessor`가 run_service 결과를 검증한다.
- `AnalysisService`의 code generation loop가 이 service를 반복 호출한다.

### 주의점

- LLM 출력은 항상 deterministic processor/sandbox 이후에만 runtime 결과로 인정된다.
- prompt 변경은 analysis planning accuracy guard가 있는 환경에서는 해당 guard와 함께 확인해야 한다.

## Hotspot: `backend/app/modules/analysis/schemas.py`

### 역할

analysis module의 Pydantic contract를 정의한다. LLM structured output, deterministic validation, sandbox result, API response가 모두 이 schema에 의존한다.

### 대표 model

- 계획 구성: `FilterCondition`, `MetricSpec`, `SortSpec`, `DerivedColumnSpec`, `IntradayFilter`, `TimeContext`, `ExpectedOutputSpec`.
- 상태/에러: `ErrorStage`, `FinalStatus`.
- 실행 계약: `AnalysisPlanDraft`, `AnalysisPlan`, `GeneratedCode`, `SandboxExecutionResult`, `AnalysisExecutionResult` 계열 model.

### 주의점

- schema field 이름은 prompt, processor, service, tests가 함께 의존한다.
- “정확도 개선” 작업은 prompt만이 아니라 schema 제약이 answer 가능 범위를 어떻게 좁히는지까지 같이 보아야 한다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: `backend/app/modules/analysis/service.py`는 planning, code generation loop, sandbox execution, result persistence를 모두 연결한다. 책임이 넓으므로 후속 변경 시 어느 단계의 문제인지 먼저 state field로 분리해 읽어야 한다.
- 관찰: `backend/app/orchestration/workflows/analysis.py`의 planning node는 내부에서 broad `Exception`을 잡아 `final_status="fail"`로 변환한다. 오류 원인 추적 시 `analysis_error.detail`과 서버 로그를 함께 확인해야 한다.
- 리스크: prompt, schema, processor allowlist가 서로 맞지 않으면 LLM이 그럴듯한 plan/code를 내도 `validate_generated_code()`나 `validate_execution_result()`에서 실패할 수 있다.
- 리스크: analysis result가 visualization/report/export로 재사용되므로 `analysis_result` payload key 변경은 module 내부 변경으로 끝나지 않는다.
