# Analysis Time Axis Source/Output Columns Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 월/일/주/연도 같은 시간 버킷 출력 컬럼이 원본 데이터셋 컬럼 검증에 섞여 분석이 실패하는 문제를 고친다.

**Architecture:** `AnalysisProcessor`의 plan normalization 단계에서 원본 입력 컬럼(source columns)과 분석 결과/시각화 출력 컬럼(output/chart columns)을 분리한다. `used_columns`와 `required_columns`는 실제 DataFrame에서 읽는 원본 컬럼만 담고, `expected_output.expected_table_columns`와 `visualization_hint`는 결과 table/chart 축 컬럼을 담도록 유지한다.

**Tech Stack:** FastAPI backend, Pydantic v2 schemas, pytest, deterministic analysis processor tests.

---

## 확인한 현재 상태

### 관찰 로그

문제 trace:

- `storage/logs/traces/25f23c0d-23e9-41cb-8e3c-0de132ea5e0b.json`
- 질문: `시간 흐름에 따라 생산량과 불량 발생 추이를 시각화해줘.`
- 실패 stage: `result_validation`
- 실패 메시지: `analysis plan references unknown columns: month`

### 재현 확인

현재 코드로 동일한 형태의 plan을 만들면 다음 상태가 된다.

```text
required_columns= ['Reason', 'TimeStamp', 'month']
used_columns= ['Reason', 'TimeStamp', 'month']
visualization_hint.x= 'month'
expected_table_columns= ['month', 'production_volume', 'defect_occurrence']
validation= fail analysis plan references unknown columns: month
```

`month`는 원본 데이터셋 컬럼이 아니라 `TimeStamp`에서 분석 중 생성되는 결과 table의 시간축 컬럼이다. 따라서 `expected_table_columns`와 `visualization_hint.x`에는 있어야 하지만 `required_columns`/`used_columns`에는 없어야 한다.

수동으로 plan의 source columns를 `['Reason', 'TimeStamp']`로 고치면 같은 payload가 정상 검증된다.

```text
corrected_required_columns= ['Reason', 'TimeStamp']
expected_table_columns= ['month', 'production_volume', 'defect_occurrence']
validation= success None complete
```

### 문제가 되는 코드 경로

1. `backend/app/modules/analysis/processor.py:146-157`
   - `time_context.grain='month'`를 정규화하고 visualization hint를 만든다.

2. `backend/app/modules/analysis/processor.py:537-559`
   - `_build_visualization_hint()`가 `time_axis_column = self._time_axis_output_column(time_context)`를 사용한다.
   - `grain='month'`면 `visualization_hint.x='month'`가 된다.

3. `backend/app/modules/analysis/processor.py:441-481`
   - `_build_required_columns()`가 `visualization_hint.x/y/series`를 source required column 후보로 추가한다.
   - 여기서 `month`가 source column으로 섞인다.

4. `backend/app/modules/analysis/processor.py:359-379`
   - `_validate_output_payload()`가 `plan.used_columns`를 `metadata_snapshot.columns`와 비교한다.
   - 실제 metadata에는 `month`가 없으므로 실패한다.

### 수정 방향 검증

수정 방향은 맞다. 단, `month` 문자열만 예외 처리하면 안 된다.

근본 계약은 다음과 같아야 한다.

```text
source/input columns:
- 실제 dataset metadata에 존재하고 df에서 읽는 컬럼
- 예: TimeStamp, Reason
- required_columns / used_columns에 포함

output/chart columns:
- 분석 결과 table 또는 chart 축에 나타나는 컬럼
- 예: month, production_volume, defect_occurrence
- expected_output.expected_table_columns / visualization_hint에 포함
```

따라서 해결은 `month` hardcode가 아니라 `time_context.grain`으로 만들어진 time-axis output column을 source column 수집에서 제외하는 것이다.

---

## Non-goals

- LLM planner prompt를 먼저 고치지 않는다. 현재 실패는 deterministic plan normalization/validation 경계에서 재현된다.
- `validate_execution_result()`의 unknown source column guard를 약화하지 않는다. 이 guard는 실제 hallucinated source column을 잡는 데 필요하다.
- frontend chart hover/click 수정 파일은 건드리지 않는다. 현재 워킹트리에 다음 uncommitted frontend 변경이 있으므로 backend 수정과 커밋을 분리한다.
  - `frontend/src/app/components/visualization/chartTheme.ts`
  - `frontend/src/app/components/visualization/renderers/BarChartCard.tsx`
  - `frontend/src/app/components/visualization/renderers/LineChartCard.tsx`
  - `frontend/src/app/components/visualization/renderers/ScatterChartCard.tsx`
- 신규 schema 필드는 추가하지 않는다. 기존 `AnalysisPlan`, `ExpectedOutputSpec`, `VisualizationHint` 계약 안에서 고친다.

---

## Target contract

월별 추세 요청의 정상 plan은 다음 형태여야 한다.

```json
{
  "required_columns": ["Reason", "TimeStamp"],
  "used_columns": ["Reason", "TimeStamp"],
  "time_context": {
    "time_column": "TimeStamp",
    "grain": "month"
  },
  "visualization_hint": {
    "preferred_chart": "line",
    "x": "month",
    "y": "production_volume"
  },
  "expected_output": {
    "expected_table_columns": ["month", "production_volume", "defect_occurrence"],
    "require_time_axis": true
  }
}
```

결과 payload는 다음 형태로 통과해야 한다.

```json
{
  "summary": "...",
  "table": [
    {
      "month": "2026-05",
      "production_volume": 10,
      "defect_occurrence": 2
    }
  ],
  "raw_metrics": {},
  "used_columns": ["TimeStamp", "Reason"]
}
```

---

## Task 1: 시간축 output column 회귀 테스트 추가

**Objective:** 현재 버그를 deterministic unit/regression test로 먼저 재현한다.

**Files:**
- Create: `backend/tests/evaluation/runtime/test_analysis_processor_time_axis_columns.py`

**Step 1: Write failing test**

테스트 파일을 새로 만들고 아래 케이스를 추가한다.

```python
from __future__ import annotations

from backend.app.modules.analysis.processor import AnalysisProcessor
from backend.app.modules.analysis.schemas import (
    AnalysisOutputPayload,
    AnalysisPlanDraft,
    MetadataSnapshot,
    MetricSpec,
    SandboxExecutionResult,
    SortSpec,
    TimeContext,
    VisualizationHint,
)


def test_month_time_axis_output_column_is_not_treated_as_source_column() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["TimeStamp", "Reason", "PassOrFail"],
        datetime_columns=["TimeStamp"],
        categorical_columns=["Reason", "PassOrFail"],
        row_count=10,
    )
    draft = AnalysisPlanDraft(
        analysis_type="time_series_visualization",
        objective="월별 생산량과 불량 발생 추이",
        metrics=[
            MetricSpec(
                name="production_volume",
                aggregation="count",
                column=None,
                alias="production_volume",
            ),
            MetricSpec(
                name="defect_occurrence",
                aggregation="count",
                column="Reason",
                alias="defect_occurrence",
            ),
        ],
        sort_by=[SortSpec(column="TimeStamp", direction="asc")],
        time_context=TimeContext(
            time_column="TimeStamp",
            range_type="none",
            grain="month",
        ),
        visualization_hint=VisualizationHint(preferred_chart="none"),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    assert plan.required_columns == ["Reason", "TimeStamp"]
    assert plan.used_columns == ["Reason", "TimeStamp"]
    assert plan.visualization_hint.x == "month"
    assert plan.visualization_hint.y == "production_volume"
    assert plan.expected_output.expected_table_columns == [
        "month",
        "production_volume",
        "defect_occurrence",
    ]

    result = processor.validate_execution_result(
        SandboxExecutionResult(
            ok=True,
            stdout_json=AnalysisOutputPayload(
                summary="월별 생산량과 불량 발생 추이입니다.",
                table=[
                    {
                        "month": "2026-05",
                        "production_volume": 10,
                        "defect_occurrence": 2,
                    }
                ],
                raw_metrics={},
                used_columns=["TimeStamp", "Reason"],
            ),
        ),
        plan,
    )

    assert result.execution_status == "success"
    assert result.quality_status == "complete"
```

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/runtime/test_analysis_processor_time_axis_columns.py
```

Expected now:

```text
FAIL
assert ['Reason', 'TimeStamp', 'month'] == ['Reason', 'TimeStamp']
```

또는 payload validation이 `analysis plan references unknown columns: month`로 실패해야 한다.

---

## Task 2: 실제 chart source column은 계속 required에 남는 guard 테스트 추가

**Objective:** time-axis output만 제외하고, 실제 원본 컬럼을 사용하는 chart 축은 required source column으로 유지되는지 보장한다.

**Files:**
- Modify: `backend/tests/evaluation/runtime/test_analysis_processor_time_axis_columns.py`

**Step 1: Add guard test**

같은 파일에 아래 테스트를 추가한다.

```python

def test_real_visualization_axis_columns_remain_required_source_columns() -> None:
    processor = AnalysisProcessor()
    metadata = MetadataSnapshot(
        columns=["Injection_Time", "Cycle_Time", "PassOrFail"],
        numeric_columns=["Injection_Time", "Cycle_Time"],
        categorical_columns=["PassOrFail"],
        row_count=10,
    )
    draft = AnalysisPlanDraft(
        analysis_type="relationship",
        objective="Injection_Time과 Cycle_Time 관계",
        metrics=[
            MetricSpec(
                name="row_count",
                aggregation="count",
                column=None,
                alias="row_count",
            )
        ],
        visualization_hint=VisualizationHint(
            preferred_chart="scatter",
            x="Injection_Time",
            y="Cycle_Time",
            series="PassOrFail",
        ),
        ambiguity_status="clear",
    )

    plan = processor.validate_and_finalize_plan(draft, metadata)

    assert plan.required_columns == ["Injection_Time", "Cycle_Time", "PassOrFail"]
    assert plan.used_columns == ["Injection_Time", "Cycle_Time", "PassOrFail"]
    assert plan.expected_output.expected_table_columns == [
        "Injection_Time",
        "Cycle_Time",
        "PassOrFail",
    ]
```

**Step 2: Verify current behavior**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/runtime/test_analysis_processor_time_axis_columns.py
```

Expected:

- 첫 번째 테스트는 실패한다.
- 두 번째 테스트는 이미 통과하거나, 구현 후 통과해야 한다.

이 테스트는 잘못된 broad fix, 예를 들어 `visualization_hint.x/y/series` 전체를 required source에서 제거하는 변경을 막는다.

---

## Task 3: `_build_required_columns()`에서 time-axis output을 source 후보에서 제외

**Objective:** `date/week/month/quarter/year/hour` 같은 time grain output axis가 `required_columns`/`used_columns`에 섞이지 않게 한다.

**Files:**
- Modify: `backend/app/modules/analysis/processor.py:441-481`

**Step 1: Implement minimal fix**

`_build_required_columns()` 내부에서 visualization hint loop 전에 time-axis output column을 계산한다.

Target shape:

```python
time_axis_output_column = self._time_axis_output_column(time_context)
metric_aliases = {metric.alias for metric in metrics if metric.alias}
if visualization_hint:
    for column in (
        visualization_hint.x,
        visualization_hint.y,
        visualization_hint.series,
    ):
        if (
            column
            and column != time_axis_output_column
            and column not in derived_names
            and column not in metric_aliases
        ):
            required.append(column)
```

이 변경이 안전한 이유:

- 원본 시간 컬럼은 이미 `if time_context and time_context.time_column: required.append(time_context.time_column)`로 들어간다.
- `month` 같은 output axis만 visualization hint loop에서 제외된다.
- 실제 원본 chart 축인 `Injection_Time`, `Cycle_Time`, `PassOrFail`은 `time_axis_output_column`과 다르므로 계속 required에 들어간다.
- metric alias는 기존처럼 source column에서 제외된다.
- derived column name도 기존처럼 source column에서 제외된다.

**Step 2: Run focused tests**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/runtime/test_analysis_processor_time_axis_columns.py
```

Expected:

```text
2 passed
```

---

## Task 4: 기존 alias/result validation 회귀 테스트 실행

**Objective:** 기존 metric alias 분리와 P0 analysis validation이 깨지지 않았는지 확인한다.

**Files:**
- Test only

**Step 1: Run related tests**

Run:

```bash
PYTHONPATH=. pytest -q \
  backend/tests/evaluation/runtime/test_analysis_processor_metric_alias.py \
  backend/tests/evaluation/runtime/test_p0_moldset_analysis_runtime.py
```

Expected:

- `test_analysis_processor_metric_alias.py` 통과
- `test_p0_moldset_analysis_runtime.py`는 로컬 raw dataset 존재 여부에 따라 실행 또는 skip될 수 있음
- 실패하면 source/output column 분리가 기존 metric alias 계약을 깨뜨렸는지 확인한다

---

## Task 5: 분석 workflow guard suite 실행

**Objective:** analysis planner/processor 변경이 main workflow와 planner guard에 영향을 주지 않았는지 확인한다.

**Files:**
- Test only

**Step 1: Run backend workflow tests**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
```

Expected:

```text
passed
```

---

## Task 6: 필요 시 문서 갱신 여부 판단

**Objective:** 코드 계약 변경이 아키텍처 문서에 반영되어야 하는지 확인한다.

**Files likely to inspect:**
- `docs/architecture/shared-state.md`
- `docs/architecture/modules/preprocess-and-visualization.md`
- `docs/architecture/orchestration/workflows.md`

**Decision rule:**

이번 수정이 내부 processor normalization bug fix로 끝나고 public payload key가 바뀌지 않으면 문서 변경은 생략한다.

단, 문서에 `used_columns`가 “그래프 축 또는 결과 컬럼을 포함한다”처럼 잘못 설명된 부분이 발견되면 다음 문장을 추가한다.

```text
analysis `used_columns`는 실제 원본 데이터셋에서 읽은 source column만 나타낸다. 시간 grain으로 생성된 `month/date/week/year` 같은 출력 축은 결과 table/chart column으로 검증되며 source column 검증 대상은 아니다.
```

문서를 수정했다면 run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py
```

---

## Task 7: graphify 갱신 및 status 확인

**Objective:** 코드 변경 후 로컬 graphify 산출물을 최신화하고 커밋 범위를 확인한다.

**Step 1: Update graph**

Run:

```bash
graphify update .
```

Expected:

```text
graph.json and GRAPH_REPORT.md updated in graphify-out
```

**Step 2: Inspect status**

Run:

```bash
git status --short --untracked-files=all
git diff --stat
```

Expected backend change set:

```text
M backend/app/modules/analysis/processor.py
A backend/tests/evaluation/runtime/test_analysis_processor_time_axis_columns.py
```

Optional docs if Task 6 required them.

현재 frontend chart hover 수정 파일이 이미 uncommitted로 존재하므로, backend 커밋 시 아래 frontend 파일을 staging하지 않는다.

```text
frontend/src/app/components/visualization/chartTheme.ts
frontend/src/app/components/visualization/renderers/BarChartCard.tsx
frontend/src/app/components/visualization/renderers/LineChartCard.tsx
frontend/src/app/components/visualization/renderers/ScatterChartCard.tsx
```

---

## Task 8: backend fix만 별도 커밋

**Objective:** 기존 frontend 실험 변경과 섞지 않고 source/output column bug fix만 커밋한다.

**Step 1: Stage backend files only**

Run:

```bash
git add backend/app/modules/analysis/processor.py \
  backend/tests/evaluation/runtime/test_analysis_processor_time_axis_columns.py
```

문서를 수정했다면 해당 docs 파일도 추가한다.

**Step 2: Commit**

Run:

```bash
git commit -m "fix: separate time-axis output columns from source columns"
```

---

## Risks and tradeoffs

- `visualization_hint.x == time_axis_output_column`인 경우만 제외해야 한다. `visualization_hint` 전체를 source에서 제외하면 scatter/bar에서 실제 원본 x/y/series 컬럼 검증이 약해진다.
- `validate_execution_result()`의 unknown source column guard를 완화하면 LLM이 없는 컬럼을 사용해도 놓칠 수 있으므로 수정 대상이 아니다.
- 데이터셋에 실제 `month` 원본 컬럼이 있고 `time_context.time_column='month'`인 경우는 괜찮다. 원본 시간 컬럼은 `time_context.time_column` 경로로 required에 추가되기 때문이다.
- planner prompt만 수정하면 LLM output 변동에 의존하게 된다. 이번 문제는 deterministic processor에서 재현되므로 processor test와 code fix가 우선이다.

---

## Final validation checklist

- [ ] 새 regression test가 구현 전 RED로 실패했다.
- [ ] `_build_required_columns()`는 time-axis output column만 source 후보에서 제외한다.
- [ ] 월별 추세 plan의 `used_columns`에는 `month`가 없다.
- [ ] 월별 추세 result table에는 `month`가 있고 validation이 성공한다.
- [ ] 실제 원본 chart axis 컬럼은 계속 `required_columns`에 남는다.
- [ ] 관련 pytest suite가 통과한다.
- [ ] `graphify update .` 실행 완료.
- [ ] backend fix 커밋이 frontend hover 실험 변경과 섞이지 않았다.
