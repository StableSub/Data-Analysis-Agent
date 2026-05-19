# Visualization Architecture Cleanup Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 시각화 결과 영역을 “검은 배경 수정” 수준이 아니라, 일관된 chart contract, 확장 가능한 렌더러 구조, 다중 차트 지원 기반까지 갖춘 구조로 정리한다.

**Architecture:** 백엔드는 chart result contract를 명시하고, 프론트엔드는 payload parsing/normalization/rendering/theme를 분리한다. 기존 `chart`/`chart_data` 호환은 유지하되, 내부 view model은 `cards[]` 기반으로 바꿔 앞으로 여러 그래프를 자연스럽게 렌더링할 수 있게 한다.

**Tech Stack:** FastAPI/Pydantic v2, pandas/matplotlib, React/Vite, TypeScript, Recharts, Tailwind utility classes.

---

## 현재 문제 요약

겉으로 보이는 문제는 “시각화 결과가 dark theme 영향을 받아 검은 배경처럼 보이는 것”이다. 하지만 코드 기준 근본 문제는 더 넓다.

1. `frontend/src/app/components/visualization/VisualizationResultView.tsx`가 너무 많은 책임을 가진다.
   - payload 선택
   - chart row 변환
   - chart config 생성
   - chart type 분기 렌더링
   - artifact 이미지 렌더링
   - caption 렌더링
   - dark/light theme 처리

2. 시각화 전용 theme가 없다.
   - chart card가 앱 전체 dark class와 섞인다.
   - `ChartContainer`는 shared primitive라 직접 수정하면 영향 범위가 크다.
   - 따라서 visualization 영역에서만 light chart theme를 고정하는 wrapper가 필요하다.

3. frontend chart contract가 단일 차트 중심이다.
   - 현재 `VisualizationResultPayload`는 `chart`, `chart_data`만 본다.
   - 사용자는 “양품/불량 비율, 불량 사유별 건수, 제품별 생산량”처럼 여러 그래프를 동시에 요청할 수 있다.
   - 미래 확장을 위해 내부 표현은 `VisualizationCard[]`로 바꾸는 편이 좋다.

4. backend visualization output contract가 여러 경로에 흩어져 있다.
   - `backend/app/modules/visualization/service.py`는 analysis result 기반 `chart`/`chart_data`를 만든다.
   - `backend/app/modules/visualization/executor.py`는 matplotlib artifact PNG를 만든다.
   - `backend/app/modules/visualization/schemas.py`에는 manual/from-analysis schema만 있고, workflow result 전체 schema는 약하다.

5. chart type 지원 범위가 일관되지 않다.
   - backend planner/executor: `scatter`, `line`, `bar`, `hist`, `box`
   - manual API schema: `bar`, `line`, `pie`, `scatter`, `heatmap`
   - frontend renderer: `line`, `scatter`, 나머지는 bar 취급
   - 이 차이는 새 차트 타입 추가 시 버그를 만들기 쉽다.

## 비목표

이번 계획은 다음을 당장 하지 않는다.

- 앱 전체 dark/light theme 체계 변경
- `components/ui/chart.tsx` 전면 수정
- 모든 chart type을 한 번에 완성
- LLM이 다중 차트 plan을 완벽하게 생성하도록 프롬프트 대개편
- 신규 frontend test framework 도입

P0는 “구조를 안전하게 분리하고 현재 기능을 깨지 않게 정리”하는 것이다.

---

## 목표 구조

### Backend result contract

기존 호환 필드:

```python
{
    "status": "generated",
    "source_id": source_id,
    "summary": "...",
    "chart": chart_data,
    "chart_data": chart_data,
    "artifact": artifact_or_none,
    "fallback_table": fallback_table_or_none,
}
```

확장 필드:

```python
{
    "charts": [chart_data_1, chart_data_2],
}
```

규칙:

- `chart_data`: 대표 차트 1개. 기존 frontend 호환용.
- `chart`: `chart_data`와 동일한 legacy alias. 제거하지 않는다.
- `charts`: 다중 차트용 canonical list. 없으면 frontend가 `chart_data`로부터 1개 card를 만든다.
- `artifact`: PNG fallback/legacy artifact. chart cards와 별도 card로 렌더링 가능.
- `fallback_table`: chart 생성 불가 시 table card로 표시 가능.

### Frontend internal view model

```ts
export type VisualizationCardKind = "chart" | "artifact" | "table";

export interface VisualizationChartCard {
  kind: "chart";
  id: string;
  chartType: "bar" | "line" | "scatter" | "hist" | "box" | "pie" | "heatmap" | string;
  title: string;
  caption?: string;
  xKey?: string;
  yKey?: string;
  rows: Record<string, unknown>[];
  seriesKeys: string[];
  config: Record<string, { label: string; color: string }>;
}

export interface VisualizationArtifactCard {
  kind: "artifact";
  id: string;
  title: string;
  caption?: string;
  mimeType: string;
  imageBase64: string;
}

export interface VisualizationTableCard {
  kind: "table";
  id: string;
  title: string;
  caption?: string;
  rows: Record<string, unknown>[];
}

export type VisualizationCard =
  | VisualizationChartCard
  | VisualizationArtifactCard
  | VisualizationTableCard;
```

`VisualizationResultView`는 이 cards를 map만 한다.

---

## Phase 1: 현상 보존 테스트와 계약 정리

### Task 1: backend visualization result schema 추가

**Objective:** workflow/API에서 쓰는 visualization result shape를 Pydantic schema로 명시한다.

**Files:**
- Modify: `backend/app/modules/visualization/schemas.py`
- Test: `backend/tests/test_visualization_result_contract.py`

**Steps:**
1. `ChartSeriesPayload`, `ChartDataPayload`, `VisualizationArtifactPayload`, `VisualizationResultPayload` schema를 추가한다.
2. `chart`와 `chart_data`는 둘 다 optional로 두고, `charts`는 optional list로 둔다.
3. `status`는 우선 기존 문자열을 허용한다. Literal을 너무 좁게 잡으면 기존 흐름을 깨기 쉽다.
4. 테스트에서 기존 `chart`/`chart_data` payload와 신규 `charts` payload가 모두 validate되는지 확인한다.

**Verification:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_visualization_result_contract.py
```

### Task 2: frontend visualization payload type 확장

**Objective:** backend 확장 필드 `charts`, `fallback_table`을 frontend 타입에 추가한다.

**Files:**
- Modify: `frontend/src/lib/visualization.ts`

**Steps:**
1. `VisualizationResultPayload`에 `charts?: VisualizationChartPayload[]`, `fallback_table?: Record<string, unknown>[]`를 추가한다.
2. `parseVisualizationResult()`에서 `charts` 배열을 parse한다.
3. 기존 `chart`/`chart_data` parsing은 유지한다.
4. `getVisualizationChartData()`는 기존 대표 차트 조회 함수로 유지한다.
5. 신규 `getVisualizationCharts()` helper를 추가한다.

**Verification:**

```bash
npm --prefix frontend run build
```

---

## Phase 2: frontend 책임 분리

### Task 3: visualization view model module 생성

**Objective:** `VisualizationResultView.tsx`에서 chart row/config 변환 로직을 분리한다.

**Files:**
- Create: `frontend/src/app/components/visualization/visualizationModel.ts`
- Modify: `frontend/src/app/components/visualization/VisualizationResultView.tsx`

**Steps:**
1. `CHART_COLORS`를 `visualizationModel.ts`로 이동한다.
2. `buildChartConfig()`와 `buildChartRows()`를 `buildVisualizationCards()` 내부 helper로 이동한다.
3. `buildVisualizationCards(visualization)`는 다음 우선순위로 card를 만든다.
   - `charts[]`가 있으면 각 chart를 card로 만든다.
   - 없으면 `chart_data` 또는 `chart` 1개를 chart card로 만든다.
   - `artifact.image_base64`가 있으면 artifact card를 만든다.
   - `fallback_table`이 있으면 table card를 만든다.
4. `VisualizationResultView.tsx`는 `const cards = buildVisualizationCards(visualization)`만 호출하게 만든다.

**Acceptance Criteria:**
- 단일 `chart_data` 결과가 기존처럼 보인다.
- `artifact` 결과가 기존처럼 보인다.
- `charts` 배열이 들어오면 여러 chart card가 순서대로 보인다.

**Verification:**

```bash
npm --prefix frontend run build
```

### Task 4: visualization theme token 추가

**Objective:** 시각화 영역만 항상 읽기 쉬운 light chart theme를 쓰게 한다.

**Files:**
- Create: `frontend/src/app/components/visualization/chartTheme.ts`
- Modify: `frontend/src/app/components/visualization/VisualizationResultView.tsx`

**Theme Contract:**

```ts
export const VISUALIZATION_CHART_THEME = {
  cardClassName: "rounded-lg bg-white text-gray-900 border border-gray-200 p-4 shadow-sm",
  imageClassName: "w-full rounded-lg bg-white border border-gray-200 shadow-sm",
  captionClassName: "text-xs text-gray-600 whitespace-pre-wrap",
  grid: "#E5E7EB",
  axis: "#D1D5DB",
  tick: "#111827",
  tooltipClassName: "bg-white text-gray-900 border-gray-200 shadow-lg",
  colors: ["#2563EB", "#16A34A", "#F97316", "#DB2777", "#7C3AED", "#0891B2"],
} as const;
```

**Rules:**
- `dark:bg-*`, `dark:text-*`, `dark:border-*`를 visualization chart card에서 제거한다.
- shared `components/ui/chart.tsx`는 수정하지 않는다.
- axis/grid/tooltip 색상은 Recharts props로 명시한다.

**Verification:**

```bash
npm --prefix frontend run build
```

### Task 5: chart renderer components 분리

**Objective:** chart type별 렌더링 분기를 독립 컴포넌트로 나눈다.

**Files:**
- Create: `frontend/src/app/components/visualization/renderers/LineChartCard.tsx`
- Create: `frontend/src/app/components/visualization/renderers/BarChartCard.tsx`
- Create: `frontend/src/app/components/visualization/renderers/ScatterChartCard.tsx`
- Create: `frontend/src/app/components/visualization/renderers/ArtifactImageCard.tsx`
- Create: `frontend/src/app/components/visualization/renderers/FallbackTableCard.tsx`
- Create: `frontend/src/app/components/visualization/renderers/UnsupportedChartCard.tsx`
- Modify: `frontend/src/app/components/visualization/VisualizationResultView.tsx`

**Steps:**
1. `LineChartCard`는 line 전용 Recharts code를 가진다.
2. `BarChartCard`는 bar/hist fallback을 담당한다. hist 전용은 아직 완성하지 않고 title/caption으로 구분한다.
3. `ScatterChartCard`는 scatter 전용 code를 가진다.
4. 지원하지 않는 chart type은 bar로 억지 렌더링하지 않고 `UnsupportedChartCard`를 표시한다.
5. `VisualizationResultView`는 `renderCard(card)`만 담당한다.

**Clean Code Rule:**
- `VisualizationResultView.tsx`는 80~120 lines 안으로 유지한다.
- `renderers/*`는 각 파일이 한 chart family만 책임진다.

**Verification:**

```bash
npm --prefix frontend run build
```

---

## Phase 3: backend chart contract 정리

### Task 6: service output에 `charts` canonical field 추가

**Objective:** analysis 기반 visualization 결과가 `charts`를 canonical list로 제공하게 한다.

**Files:**
- Modify: `backend/app/modules/visualization/service.py`
- Test: `backend/tests/test_visualization_result_contract.py`

**Steps:**
1. `build_from_analysis_result()`에서 `chart_data`가 있으면 `charts = [chart_data]`를 추가한다.
2. 기존 `chart`와 `chart_data`는 유지한다.
3. `fallback_table`은 유지한다.
4. 테스트에서 `chart`, `chart_data`, `charts[0]`가 동일한 대표 차트를 가리키는지 확인한다.

**Verification:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_visualization_result_contract.py
```

### Task 7: executor artifact output도 result schema를 통과하게 정리

**Objective:** matplotlib artifact 경로도 같은 result schema를 따른다.

**Files:**
- Modify: `backend/app/modules/visualization/executor.py`
- Test: `backend/tests/test_visualization_executor_contract.py`

**Steps:**
1. `execute_visualization_plan()` 성공 결과에 `charts: []`를 추가한다.
2. `artifact`는 기존 그대로 둔다.
3. `_build_unavailable_result()`도 최소 schema를 만족하게 유지한다.
4. 성공/unavailable 결과가 `VisualizationResultPayload.model_validate()`를 통과하는지 테스트한다.

**Verification:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_visualization_executor_contract.py
```

### Task 8: matplotlib style helper 정리

**Objective:** PNG artifact도 항상 흰 배경/검은 글씨로 생성되게 한다.

**Files:**
- Modify: `backend/app/modules/visualization/executor.py`
- Test: `backend/tests/test_visualization_executor_contract.py`

**Steps:**
1. `_build_python_code()`의 header에 `plt.style.use('default')`를 추가한다.
2. `plt.figure(figsize=(8, 5))` 대신 `fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')`를 사용한다.
3. 가능하면 `plt.*` 호출을 `ax.*` 호출로 점진 변경한다.
4. footer에서 저장 옵션을 명시한다.

```python
fig.patch.set_facecolor('white')
ax.set_facecolor('white')
ax.tick_params(colors='#111827')
ax.xaxis.label.set_color('#111827')
ax.yaxis.label.set_color('#111827')
ax.title.set_color('#111827')
ax.grid(True, color='#E5E7EB', linewidth=0.8, alpha=0.8)
plt.tight_layout()
plt.savefig(output_path, dpi=150, facecolor='white', edgecolor='white', transparent=False)
```

**Verification:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_visualization_executor_contract.py
```

---

## Phase 4: chart type registry로 확장성 확보

### Task 9: backend chart type registry 추가

**Objective:** chart type literal과 required column rule을 한 곳에서 관리한다.

**Files:**
- Create: `backend/app/modules/visualization/chart_registry.py`
- Modify: `backend/app/modules/visualization/planner.py`
- Modify: `backend/app/modules/visualization/schemas.py`
- Test: `backend/tests/test_visualization_chart_registry.py`

**Initial Registry:**

```python
CHART_TYPES = ("bar", "line", "scatter", "hist", "box")

CHART_COLUMN_REQUIREMENTS = {
    "bar": {"x": "categorical_or_datetime", "y": "numeric"},
    "line": {"x": "datetime_or_numeric", "y": "numeric"},
    "scatter": {"x": "numeric", "y": "numeric"},
    "hist": {"x": "numeric", "y": "optional"},
    "box": {"x": "optional_categorical", "y": "numeric"},
}
```

**Steps:**
1. `CHART_KEYWORDS`는 planner에 남기되 chart type 목록은 registry를 참조한다.
2. `VisualizationPlan.chart_type` Literal은 당장은 유지해도 된다. 더 큰 변경을 피하기 위해 registry와 Literal이 동기화되는 테스트를 둔다.
3. manual API schema와 planner/executor 지원 chart type 차이를 문서화한다.

**Verification:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_visualization_chart_registry.py
```

### Task 10: frontend chart renderer registry 추가

**Objective:** chart type별 renderer mapping을 한 곳에서 관리한다.

**Files:**
- Create: `frontend/src/app/components/visualization/renderers/registry.tsx`
- Modify: `frontend/src/app/components/visualization/VisualizationResultView.tsx`

**Steps:**
1. `const CHART_RENDERERS = { line: LineChartCard, bar: BarChartCard, scatter: ScatterChartCard }`를 만든다.
2. `hist`, `box`, `pie`, `heatmap`은 `UnsupportedChartCard` 또는 명시적 placeholder로 보낸다.
3. 신규 chart type을 추가할 때 registry만 수정하면 되게 한다.

**Verification:**

```bash
npm --prefix frontend run build
```

---

## Phase 5: 다중 차트 기반 마련

### Task 11: frontend 다중 chart fixture로 build 검증

**Objective:** backend가 아직 `charts`를 여러 개 만들지 않아도 frontend가 다중 chart payload를 받을 준비가 되었는지 확인한다.

**Files:**
- Create: `frontend/src/app/components/visualization/fixtures.ts`
- Modify: `frontend/src/app/components/visualization/visualizationModel.ts`

**Steps:**
1. `multiChartVisualizationFixture`를 만든다.
2. 예시 charts:
   - `pass_fail_ratio`: bar 또는 pie placeholder
   - `defect_reason_count`: bar
   - `product_output_count`: bar
3. fixture는 dev/debug용 export만 한다. runtime 화면에는 연결하지 않는다.
4. `buildVisualizationCards(multiChartVisualizationFixture)`가 TypeScript compile을 통과하게 한다.

**Verification:**

```bash
npm --prefix frontend run build
```

### Task 12: backend 다중 chart는 별도 P1로 보류

**Objective:** P0에서 LLM/planner 복잡도를 늘리지 않고, contract와 renderer 기반만 먼저 완성한다.

**Files:**
- Modify: `docs/architecture/modules/preprocess-and-visualization.md`

**Decision:**
- P0: backend는 `charts` field를 제공하되 단일 차트만 넣는다.
- P1: analysis planner가 여러 metric/table을 만들 수 있을 때 `charts[]`를 실제 다중 생성한다.
- P1: “비율 + 사유별 건수 + 제품별 생산량” 같은 요청을 sub-chart intents로 분해한다.

**Verification:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py
```

---

## Phase 6: 문서와 최종 검증

### Task 13: architecture 문서 갱신

**Objective:** 변경된 시각화 contract와 frontend renderer 구조를 문서화한다.

**Files:**
- Modify: `docs/architecture/modules/preprocess-and-visualization.md`
- Modify: `docs/system/frontend-structure.md`

**내용:**
1. `VisualizationResultPayload` 주요 필드 설명
2. `chart`/`chart_data` legacy alias 정책
3. `charts[]` canonical list 정책
4. frontend renderer 위치
5. visualization 영역은 앱 theme와 별도로 light chart theme를 사용한다는 결정
6. chart type 지원 범위와 미지원 chart type 처리 방식

**Verification:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py
npm --prefix frontend run build
```

### Task 14: 전체 변경 검증

**Objective:** 관련 backend/frontend 검증을 한 번에 수행한다.

**Commands:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_visualization_result_contract.py backend/tests/test_visualization_executor_contract.py backend/tests/test_visualization_chart_registry.py
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py
npm --prefix frontend run build
```

**Optional after code changes:**

```bash
graphify update .
```

`graphify-out/` 전체는 로컬 생성물로 다루고, 필요한 문서/코드 변경만 커밋한다.

---

## 권장 구현 순서

1. `frontend/src/app/components/visualization/visualizationModel.ts`부터 만든다.
2. `chartTheme.ts`를 만들고 light chart theme를 고정한다.
3. renderer components를 분리한다.
4. backend result schema와 `charts` field를 추가한다.
5. matplotlib artifact style을 고정한다.
6. chart registry는 마지막에 추가한다.
7. 문서를 갱신한다.

이 순서가 좋은 이유:

- 사용자에게 보이는 문제는 frontend에서 가장 빨리 안정화된다.
- shared `ChartContainer`를 건드리지 않아 사이드 이펙트를 줄인다.
- backend contract 변경은 backward compatible하게 들어간다.
- 다중 차트는 UI/view model부터 준비하고, LLM planner 확장은 별도 단계로 남긴다.

## Definition of Done

- 시각화 chart card와 artifact image는 dark mode에서도 흰 배경/검은 텍스트로 보인다.
- `VisualizationResultView.tsx`는 orchestration/render dispatch만 담당한다.
- chart row/config 변환은 `visualizationModel.ts`에 있다.
- chart type별 renderer는 `renderers/` 아래에 있다.
- backend result는 `VisualizationResultPayload` schema로 validate 가능하다.
- 기존 `chart`/`chart_data` payload는 깨지지 않는다.
- 신규 `charts[]` payload를 frontend가 여러 card로 렌더링할 수 있다.
- 검증 명령이 통과한다.

## 예상 리스크와 대응

1. 리스크: frontend test framework가 없어 UI regression을 자동화하기 어렵다.
   - 대응: P0에서는 `npm --prefix frontend run build`로 타입/빌드 안정성을 확인한다.
   - P1에서 Vitest/React Testing Library 도입 여부를 별도 판단한다.

2. 리스크: chart type 지원 범위가 backend/frontend/manual API마다 다르다.
   - 대응: registry와 문서로 차이를 드러내고, 미지원 타입은 fallback card로 표시한다.

3. 리스크: `components/ui/chart.tsx`를 수정하면 다른 화면에 영향이 갈 수 있다.
   - 대응: shared primitive는 건드리지 않고 visualization feature layer에서 theme를 주입한다.

4. 리스크: 다중 차트 backend planner를 바로 넣으면 LLM prompt/approval 흐름이 커진다.
   - 대응: P0는 payload/view model만 준비하고, planner 다중 분해는 P1로 분리한다.

5. 리스크: matplotlib code string refactor가 한 번에 커질 수 있다.
   - 대응: style 고정만 먼저 적용하고, script builder 분리는 후속 cleanup으로 둔다.
