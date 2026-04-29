# Preprocess and visualization modules

`backend/app/modules/preprocess/`는 데이터 정제·변환 계획과 적용을 담당하고, `backend/app/modules/visualization/`은 chart plan/result를 만든다. 두 module 모두 orchestration subgraph에서 approval interrupt와 연결되므로 state key와 pending approval payload가 중요하다.

## `preprocess/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/preprocess/__init__.py` | preprocess package marker다. |
| `backend/app/modules/preprocess/dependencies.py` | `PreprocessProcessor`, `PreprocessService` dependency builder/getter를 제공한다. |
| `backend/app/modules/preprocess/executor.py` | 승인된 preprocess plan을 실제 데이터프레임에 적용하는 `execute_preprocess_plan()`을 제공한다. |
| `backend/app/modules/preprocess/planner.py` | LLM 기반 preprocess decision/plan/review payload 생성과 revision instruction 처리를 담당한다. |
| `backend/app/modules/preprocess/processor.py` | preprocess operation을 pandas DataFrame에 적용하는 deterministic processor다. |
| `backend/app/modules/preprocess/router.py` | `APIRouter(prefix="/preprocess")`로 `POST /preprocess/apply`를 제공한다. |
| `backend/app/modules/preprocess/schemas.py` | drop/impute/rename/scale/derived/encode 등 preprocess operation schema를 정의한다. |
| `backend/app/modules/preprocess/service.py` | dataset profile 생성, preprocess apply, output path/summary/diff 생성을 담당한다. |

## `visualization/` 파일 카탈로그

| 파일 | 역할 |
|---|---|
| `backend/app/modules/visualization/__init__.py` | visualization package marker다. |
| `backend/app/modules/visualization/dependencies.py` | `VisualizationService` dependency builder/getter를 제공한다. |
| `backend/app/modules/visualization/executor.py` | visualization plan을 실행해 chart result 또는 unavailable result를 생성한다. |
| `backend/app/modules/visualization/planner.py` | LLM/heuristic 기반 chart selection, plan, review payload, revision instruction을 만든다. |
| `backend/app/modules/visualization/processor.py` | analysis result를 chart spec/data로 변환하는 deterministic processor다. |
| `backend/app/modules/visualization/router.py` | `APIRouter(prefix="/vizualization")`로 manual/from-analysis route를 제공한다. |
| `backend/app/modules/visualization/schemas.py` | chart columns, manual visualization request/response, from-analysis request schema를 정의한다. |
| `backend/app/modules/visualization/service.py` | dataset sample/preview rows, manual chart data, analysis result 기반 visualization 생성을 담당한다. |

## Public route 요약

### `backend/app/modules/preprocess/router.py`

- `POST /preprocess/apply`: preprocess operation list를 dataset에 적용한다.

### `backend/app/modules/visualization/router.py`

- `POST /vizualization/manual`: 사용자가 지정한 chart column/type 기준으로 preview chart data를 만든다.
- `POST /vizualization/from-analysis`: 저장된 analysis result를 기반으로 visualization을 만든다.

## Hotspot: `backend/app/modules/preprocess/planner.py`

### 역할

preprocess가 필요한지 판단하고, 필요한 경우 user approval에 올릴 plan/review payload를 만든다.

### 주요 class/function

- `PreprocessDecision`: preprocess 실행 여부와 이유를 담는다.
- `PreprocessPlan`: 실행할 operation list와 설명을 담는다.
- `build_preprocess_decision(...)`: 질문/profile 기반으로 preprocess 필요 여부를 판단한다.
- `build_preprocess_plan(...)`: operation plan을 생성한다.
- `build_preprocess_review_payload(...)`: approval card에 필요한 title/summary/plan/review 구조를 만든다.
- `get_revision_instruction(...)`: resume payload의 revision instruction을 읽는다.

### 연결 관계

- `backend/app/orchestration/workflows/preprocess.py`의 `preprocess_decision`, `planner`, `approval_gate` node와 직접 연결된다.
- `backend/app/modules/preprocess/service.py`와 `processor.py`가 실제 적용을 담당한다.

### 주의점

- approval payload는 `pending_approval.stage="preprocess"`, `pending_approval.kind="plan_review"` 계약을 따른다.
- revise decision이 들어오면 `revision_request.stage="preprocess"`가 다음 planner 호출에 반영된다.

## Hotspot: `backend/app/modules/preprocess/processor.py`

### 역할

`PreprocessProcessor`는 plan operation을 실제 pandas DataFrame에 적용한다.

### 주요 책임

- missing row/column drop, impute, rename, scale, derived column, categorical encoding 등 schema에 정의된 operation을 실행한다.
- `_SAFE_EXPR_RE` 기준으로 derived expression 적용 범위를 제한한다.

### 연결 관계

- `backend/app/modules/preprocess/service.py`가 `apply_operations()`를 호출한다.
- orchestration은 processor를 직접 호출하지 않고 `PreprocessService`와 workflow wrapper를 통해 결과만 받는다.

## Hotspot: `backend/app/modules/preprocess/service.py`

### 역할

`PreprocessService`는 profile 생성, plan 적용, output dataset 저장, diff/summary 계산을 묶는다.

### 주요 method/helper

- `build_dataset_profile(...)`: source dataset profile을 만든다.
- `apply(...)`: preprocess plan을 적용하고 output source id/path/summary/diff를 반환한다.
- `_build_output_path(...)`: preprocess output 파일 경로를 만든다.
- `_build_summary(...)`, `_build_diff(...)`: 사용자에게 보여줄 변화 요약을 만든다.

## Hotspot: `backend/app/modules/visualization/planner.py`

### 역할

사용자 요청과 dataset profile/sample을 기준으로 chart plan을 만든다. chart type keyword, column resolution, fallback chart selection을 함께 다룬다.

### 주요 class/function

- `VisualizationPlan`: chart 계획 schema다.
- `ChartSelection`: chart type/columns 선택 결과다.
- `build_visualization_plan(...)`: user input, profile, revision request를 받아 plan을 만든다.
- `build_visualization_review_payload(...)`: approval card payload를 만든다.
- `get_revision_instruction(...)`: visualization revise instruction을 읽는다.
- `_resolve_columns(...)`, `_recommend_chart(...)`, `_detect_requested_chart_type(...)`, `_select_chart(...)`: chart 선택 helper다.

### 주의점

- approval payload는 `pending_approval.stage="visualization"`, `pending_approval.kind="plan_review"` 계약을 따른다.
- analysis result가 이미 있으면 orchestration workflow에서 planner approval 없이 `analysis_generated` 경로로 바로 chart result를 만들 수 있다.

## Hotspot: `backend/app/modules/visualization/executor.py`

### 역할

visualization plan을 실행해 chart data/spec/result를 만든다.

### 주요 function/constant

- `execute_visualization_plan(...)`: approved plan 또는 current plan을 실행한다.
- `_build_unavailable_result(...)`: chart 생성이 불가한 경우의 result를 만든다.
- `_chart_has_data(...)`: chart data 존재 여부를 확인한다.
- `_run_chart_script(...)`, `_build_python_code(...)`: Python script 기반 chart data 생성을 담당한다.
- `PYTHON_EXECUTABLE`, `SCRIPT_TIMEOUT_SECONDS`: script 실행 환경 상수다.

## Hotspot: `backend/app/modules/visualization/service.py`

### 역할

`VisualizationService`는 source file resolution, sample frame loading, preview rows, manual visualization, analysis result 기반 visualization 생성을 담당한다.

### 연결 관계

- public router의 manual/from-analysis route에서 직접 사용된다.
- `backend/app/orchestration/workflows/visualization.py`가 approval 후 executor와 함께 사용한다.
- `backend/app/modules/analysis/service.py`가 analysis result와 visualization output 연결을 위해 이 service와 연결된다.

## 발견한 문제점 / 확인 필요 사항

- 관찰: visualization public prefix는 실제 코드상 `/vizualization`이다. 철자 차이를 문서에서 숨기면 frontend/API 호출 추적이 어려워진다.
- 관찰: preprocess와 visualization은 모두 approval interrupt를 사용하지만 stage/kind 값이 다르다. frontend state와 resume API는 이 exact value에 의존한다.
- 관찰: visualization workflow는 `analysis_result`와 `analysis_plan`이 있으면 `analysis_generated`로 바로 끝날 수 있다. 모든 visualization이 approval을 거친다고 보면 실제 흐름과 다르다.
- 리스크: preprocess output이 `output_source_id`로 다음 단계 source를 바꾸므로, 이후 analysis/rag/visualization이 원본과 전처리 결과 중 어느 source를 보는지 `resolve_target_source_id()` 흐름을 확인해야 한다.
- 리스크: chart 생성 실패가 “실패”인지 “데이터 없음/unavailable”인지 result status와 summary를 구분해야 한다.
