# Preprocess Routing and Plan Validation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 집계/시각화 질문이 불필요하게 전처리 경로로 들어가 `PreprocessPlan` validation error를 내는 문제를, 프로젝트 방향성에 맞게 route 정확도·plan contract·실패 처리 관점에서 해결한다.

**Architecture:** 핵심 수정은 세 seam에 나눈다. `planner`는 원본 데이터로 가능한 집계/시각화 질문을 analysis+visualization 경로로 보내고, `preprocess planner`는 operation별 필수 필드를 명확히 요구하며, `preprocess workflow`는 structured plan validation 실패를 raw exception이 아닌 workflow 실패 상태로 정리한다.

**Tech Stack:** FastAPI, LangGraph, Pydantic v2, LangChain structured output, pytest.

---

## 아주 쉽게 말하면

지금 문제는 “차트를 그려달라”는 요청이 “데이터를 고쳐야 한다”는 전처리 단계로 잘못 들어간 것입니다.

예를 들어 사용자가:

> 양품과 불량의 비율, 불량 사유별 건수, 제품별 생산량을 그래프로 보여줘

라고 하면 원래는:

1. `PassOrFail`로 count/ratio 계산
2. `Reason`으로 count 계산
3. `PART_NO` 또는 `PART_NAME`으로 count 계산
4. 차트 생성

이면 됩니다.

그런데 현재는 planner가 `preprocess_required=true`로 판단해서 전처리 계획을 만들었고, 그 계획 안의 `scale` operation에 `method`가 빠져 Pydantic validation error가 발생했습니다.

따라서 해결은 단순히 `scale.method` 기본값을 넣는 것이 아니라:

1. 애초에 이런 질문은 preprocess로 보내지 않게 하고
2. 진짜 preprocess가 필요할 때는 plan 필수 필드를 빠뜨리지 않게 하고
3. 그래도 plan이 깨지면 사용자가 raw Pydantic error를 보지 않게 하는 것입니다.

---

## 현재 확인한 근거

### 로그 근거

Trace ID:

`ed7b2a9e-aee7-40d8-8439-900503954689`

확인 위치:

- `storage/logs/traces/ed7b2a9e-aee7-40d8-8439-900503954689.json`
- `storage/logs/agent-trace.jsonl`

로그상 흐름:

1. 사용자 질문은 집계/시각화 요청이다.
2. `PlannerDecision`이 `preprocess_required=True`, `need_visualization=True`로 판단했다.
3. workflow가 `preprocess_flow`로 들어갔다.
4. EDA recommendation이 scale operation을 포함한 전처리 추천을 만들었다.
5. 이후 `PreprocessPlan` validation에서 `scale.method` 누락으로 실패했다.

### 코드 근거

필수 필드 정의:

`backend/app/modules/preprocess/schemas.py`

```python
class ScaleOperation(StrictModel):
    op: Literal["scale"]
    columns: list[str]
    method: Literal["standardize", "normalize"]
```

현재 planner prompt 위치:

`backend/app/modules/planner/service.py`

현재 preprocess plan prompt 위치:

`backend/app/modules/preprocess/planner.py`

현재 preprocess workflow 위치:

`backend/app/orchestration/workflows/preprocess.py`

---

## 구현 원칙

1. 최소 diff로 수정한다.
2. `ScaleOperation.method` 기본값만 넣는 증상 패치는 우선하지 않는다.
3. broad `except Exception` fallback을 추가하지 않는다.
4. “시각화 요청이면 무조건 preprocess 아님” 같은 과한 규칙을 넣지 않는다.
5. 명시적 전처리 요청은 계속 preprocess로 보내야 한다.
6. 실패는 숨기지 말고 trace 가능한 `preprocess_failed` 상태로 정리한다.
7. 테스트를 먼저 추가해 route 정확도 회귀를 고정한다.

---

## 단계별 코드 수정 순서

## Phase 0. 기준 확인

### Task 0.1: 현재 git log 스타일 확인

**Objective:** 커밋 메시지 형식을 현재 repo 스타일과 사용자 요구에 맞춘다.

**확인 결과:** 최근 git log는 아래처럼 `type(scope): message` 또는 `type: message`를 섞어 사용한다.

```text
docs(benchmark): add P0/P1 implementation findings
test(benchmark): add P0/P1 deterministic evaluation suite
test: include error metadata in SSE contract fixture
fix(chat): include status and error details in SSE error payload
```

**이번 작업의 커밋 메시지 규칙:** 사용자가 요청한 대로 scope 없이 `기능: 변경 내용` 형식만 사용한다.

예:

```text
test: 집계 시각화 질문 라우팅 회귀 추가
fix: 집계 시각화 질문 전처리 오판 방지
```

---

## Phase 1. Route regression test 추가

### Task 1.1: planner route accuracy 테스트 파일 위치 결정

**Objective:** 이번 문제의 root cause인 `preprocess_required=True` 오판을 테스트로 고정한다.

**Files:**

- Create 또는 Modify: `backend/tests/test_planner_route_accuracy.py`
- 참고: 현재 `backend/tests/test_planner_analysis_accuracy_guards.py`, `backend/tests/test_analysis_planning_accuracy_guards.py`는 문서에는 언급되지만 실제 파일은 없다.
- 참고 가능 파일:
  - `backend/tests/evaluation/workflow/test_p0_moldset_workflow_contracts.py`
  - `backend/tests/evaluation/runtime/test_p0_moldset_analysis_runtime.py`

**설계:**

새 테스트는 live LLM을 호출하지 않아야 한다. planner route 보정 helper를 순수 함수로 분리해 deterministic test를 작성한다.

새 helper 후보:

`backend/app/modules/planner/service.py`

```python
def _should_force_skip_preprocess_for_analysis_request(user_input: str) -> bool:
    ...
```

또는 더 명확히:

```python
def _is_plain_aggregate_visualization_request(user_input: str) -> bool:
    ...
```

**Step 1: 실패 테스트 작성**

`backend/tests/test_planner_route_accuracy.py`

테스트 의도:

```python
from backend.app.modules.planner.service import _should_force_skip_preprocess_for_analysis_request


def test_aggregate_visualization_request_does_not_require_preprocess() -> None:
    question = "양품과 불량의 비율, 불량 사유별 건수, 제품별 생산량을 각각 적절한 그래프로 시각화해줘."

    assert _should_force_skip_preprocess_for_analysis_request(question) is True
```

**Step 2: 반대 케이스 테스트 작성**

명시적 전처리 요청은 preprocess를 유지해야 한다.

```python
def test_explicit_preprocess_request_keeps_preprocess_path() -> None:
    question = "수치형 컬럼을 표준화한 뒤 불량 여부와의 관계를 분석해줘."

    assert _should_force_skip_preprocess_for_analysis_request(question) is False
```

**Step 3: 테스트 실패 확인**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_planner_route_accuracy.py
```

Expected:

- helper가 아직 없어서 import error 또는 test fail

---

### Task 1.2: route 보정 helper 최소 구현

**Objective:** LLM이 집계/시각화 질문을 preprocess로 잘못 판단했을 때 좁게 보정한다.

**Files:**

- Modify: `backend/app/modules/planner/service.py`
- Test: `backend/tests/test_planner_route_accuracy.py`

**구현 방향:**

helper는 아래 조건을 만족할 때만 true를 반환한다.

1. 질문에 집계/시각화 성격 키워드가 있다.
   - 비율
   - 건수
   - 생산량
   - count
   - ratio
   - 그래프
   - 시각화
   - 차트
2. 질문에 명시적 전처리 키워드가 없다.
   - 전처리
   - 결측
   - 결측치
   - 정규화
   - 표준화
   - 스케일
   - 인코딩
   - 형변환
   - 파생 컬럼
   - 컬럼명 변경
   - 제거한 뒤
   - 채운 뒤

예상 구현 형태:

```python
def _should_force_skip_preprocess_for_analysis_request(user_input: str) -> bool:
    text = user_input.lower()
    analysis_terms = (
        "비율",
        "건수",
        "생산량",
        "그래프",
        "시각화",
        "차트",
        "count",
        "ratio",
    )
    preprocess_terms = (
        "전처리",
        "결측",
        "결측치",
        "정규화",
        "표준화",
        "스케일",
        "scale",
        "normalize",
        "standardize",
        "인코딩",
        "형변환",
        "파생",
        "컬럼명",
    )
    return any(term in text for term in analysis_terms) and not any(
        term in text for term in preprocess_terms
    )
```

**주의:** 이 helper는 완벽한 intent classifier가 아니라 LLM 오판을 막는 좁은 guard다. 범위를 넓히지 않는다.

**Step 1: helper 구현**

`backend/app/modules/planner/service.py` 하단 또는 prompt 근처에 추가한다.

**Step 2: 테스트 실행**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_planner_route_accuracy.py
```

Expected:

- 2 passed

---

### Task 1.3: PlannerService.plan에 보정 적용

**Objective:** LLM의 `decision.preprocess_required=True`가 집계/시각화 질문에서만 false로 보정되도록 한다.

**Files:**

- Modify: `backend/app/modules/planner/service.py`
- Test: `backend/tests/test_planner_route_accuracy.py`

**수정 위치:**

`PlannerService.plan(...)` 내부에서 `_build_decision(...)` 직후.

현재 흐름:

```python
decision = self._build_decision(...)
if not bool((guideline_context or {}).get("has_evidence", False)):
    decision.guideline_context_used = False
route = self._resolve_route(decision)
```

수정 방향:

```python
decision = self._build_decision(...)
if _should_force_skip_preprocess_for_analysis_request(user_input):
    decision.preprocess_required = False
if not bool((guideline_context or {}).get("has_evidence", False)):
    decision.guideline_context_used = False
route = self._resolve_route(decision)
```

**주의:**

- `need_visualization`은 건드리지 않는다.
- `ask_analysis`도 건드리지 않는다.
- 명시적 전처리 요청은 helper가 false이므로 기존 LLM 판단을 유지한다.

**추가 테스트 후보:**

LLM을 호출하지 않고 `PlannerDecision` 보정 helper를 별도 함수로 분리하면 더 쉽게 테스트할 수 있다.

예:

```python
def _apply_planner_decision_guards(decision: PlannerDecision, user_input: str) -> PlannerDecision:
    if _should_force_skip_preprocess_for_analysis_request(user_input):
        decision.preprocess_required = False
    return decision
```

테스트:

```python
from backend.app.modules.planner.schemas import PlannerDecision
from backend.app.modules.planner.service import _apply_planner_decision_guards


def test_guard_overrides_only_preprocess_required_for_plain_visualization() -> None:
    decision = PlannerDecision(
        is_general_question=False,
        ask_analysis=True,
        preprocess_required=True,
        need_visualization=True,
    )

    guarded = _apply_planner_decision_guards(
        decision,
        "양품과 불량의 비율, 불량 사유별 건수, 제품별 생산량을 각각 적절한 그래프로 시각화해줘.",
    )

    assert guarded.preprocess_required is False
    assert guarded.need_visualization is True
    assert guarded.ask_analysis is True
```

**Step 1: guard 함수 테스트 추가**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_planner_route_accuracy.py
```

Expected:

- 새 테스트 fail

**Step 2: guard 함수 구현 및 `PlannerService.plan`에 적용**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_planner_route_accuracy.py
```

Expected:

- pass

---

### Commit 1

```bash
git add backend/app/modules/planner/service.py backend/tests/test_planner_route_accuracy.py
git commit -m "fix: 집계 시각화 질문 전처리 오판 방지"
```

커밋을 test와 fix로 더 쪼개고 싶으면 아래처럼 나눈다.

```bash
git add backend/tests/test_planner_route_accuracy.py
git commit -m "test: 집계 시각화 질문 라우팅 회귀 추가"

git add backend/app/modules/planner/service.py
git commit -m "fix: 집계 시각화 질문 전처리 오판 방지"
```

추천은 두 커밋으로 분리하는 것이다. 테스트 의도와 구현 변경이 git history에서 분명해진다.

---

## Phase 2. Planner prompt 보강

### Task 2.1: PlannerDecision prompt에 예시 추가

**Objective:** LLM 판단 자체가 더 안정적으로 `preprocess_required=false`를 내도록 한다.

**Files:**

- Modify: `backend/app/modules/planner/service.py`
- Test: `backend/tests/test_planner_route_accuracy.py`

**수정 위치:**

`PROMPTS["decision.system"]`

현재 문장 뒤에 예시를 추가한다.

현재 핵심 문장:

```python
"월/주/일 버킷팅, 최근 N개월 필터링, 집계, 비교, 추세 분석은 전처리가 아니라 분석이므로 그 이유만으로 preprocess_required를 true로 두지 마라. "
```

추가할 의미:

```text
양품/불량 비율, 사유별 건수, 제품별 생산량, 그룹별 count, 차트/그래프/시각화 요청은 원본 컬럼으로 계산 가능한 분석/시각화다. 사용자가 결측치 처리, 정규화, 표준화, 인코딩, 형변환 같은 전처리를 명시하지 않았다면 preprocess_required=false로 둔다.
```

**주의:** prompt에 너무 많은 예시를 넣지 않는다. 이번 문제와 같은 집계/시각화 오판만 막는다.

**Step 1: prompt 수정**

**Step 2: 테스트 실행**

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_planner_route_accuracy.py
```

Expected:

- pass

---

### Commit 2

```bash
git add backend/app/modules/planner/service.py
git commit -m "fix: planner 집계 시각화 전처리 기준 명확화"
```

---

## Phase 3. PreprocessPlan operation contract 강화

### Task 3.1: preprocess plan prompt에 op별 필수 필드 명시

**Objective:** 진짜 preprocess가 필요한 경우 `scale.method` 같은 필수 필드가 누락되지 않도록 한다.

**Files:**

- Modify: `backend/app/modules/preprocess/planner.py`
- Test 후보: `backend/tests/test_preprocess_plan_contract.py`

**수정 위치:**

`backend/app/modules/preprocess/planner.py`

`PROMPTS["plan.system"]`

현재는 지원 연산 목록과 “op+파라미터” 정도만 설명한다. 여기에 필수 필드 목록을 추가한다.

추가할 의미:

```text
operation별 필수 필드:
- drop_missing: op, columns, how
- impute: op, columns, method, value
- drop_columns: op, columns
- rename_columns: op, rename_from, rename_to
- scale: op, columns, method. method는 "standardize" 또는 "normalize". 판단이 어렵다면 "standardize".
- derived_column: op, name, source_columns, transform_type, params
- parse_datetime: op, columns, format
- outlier: op, columns, method, strategy
- encode_categorical: op, columns, method
```

**중요:** 이 단계에서는 `ScaleOperation.method`에 기본값을 넣지 않는다. plan이 어떤 스케일링을 수행하는지 approval card와 trace에서 명확히 보이게 한다.

---

### Task 3.2: PreprocessPlan schema validation 테스트 추가

**Objective:** `scale` operation은 method가 있어야 한다는 contract를 테스트로 문서화한다.

**Files:**

- Create: `backend/tests/test_preprocess_plan_contract.py`
- Modify: 없음

**Test 1: 올바른 scale plan은 통과**

```python
from backend.app.modules.preprocess.planner import PreprocessPlan


def test_preprocess_plan_accepts_scale_with_method() -> None:
    plan = PreprocessPlan.model_validate(
        {
            "operations": [
                {
                    "op": "scale",
                    "columns": ["Mold_Temperature_12"],
                    "method": "standardize",
                }
            ],
            "planner_comment": "수치형 컬럼을 표준화합니다.",
        }
    )

    assert plan.operations[0].op == "scale"
    assert plan.operations[0].method == "standardize"
```

**Test 2: method 없는 scale plan은 validation fail**

```python
import pytest
from pydantic import ValidationError
from backend.app.modules.preprocess.planner import PreprocessPlan


def test_preprocess_plan_rejects_scale_without_method() -> None:
    with pytest.raises(ValidationError, match="scale.method"):
        PreprocessPlan.model_validate(
            {
                "operations": [
                    {
                        "op": "scale",
                        "columns": ["Mold_Temperature_12"],
                    }
                ],
                "planner_comment": "수치형 컬럼을 표준화합니다.",
            }
        )
```

**Run:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_preprocess_plan_contract.py
```

Expected:

- pass

이 테스트는 “method 기본값을 넣지 않는 정책”도 함께 고정한다.

---

### Commit 3

```bash
git add backend/app/modules/preprocess/planner.py backend/tests/test_preprocess_plan_contract.py
git commit -m "fix: 전처리 계획 필수 필드 계약 강화"
```

테스트를 따로 나누려면:

```bash
git add backend/tests/test_preprocess_plan_contract.py
git commit -m "test: 전처리 계획 scale 계약 추가"

git add backend/app/modules/preprocess/planner.py
git commit -m "fix: 전처리 계획 필수 필드 안내 강화"
```

---

## Phase 4. preprocess planning ValidationError를 workflow 실패로 정리

### Task 4.1: preprocess planner failure state 테스트 추가

**Objective:** `build_preprocess_plan(...)` 단계에서 validation 실패가 발생해도 raw exception이 사용자에게 새지 않고 `preprocess_failed` output으로 정리되게 한다.

**Files:**

- Create 또는 Modify: `backend/tests/test_preprocess_workflow_error_handling.py`
- Modify 대상 예정: `backend/app/orchestration/workflows/preprocess.py`

**테스트 전략:**

LangGraph 전체를 무겁게 돌리기보다 `planner_node`에서 사용할 helper를 분리해 테스트한다.

새 helper 후보:

`backend/app/orchestration/workflows/preprocess.py`

```python
def _build_preprocess_plan_failed_output(exc: ValidationError) -> dict[str, Any]:
    ...
```

테스트:

```python
from pydantic import ValidationError
from backend.app.modules.preprocess.planner import PreprocessPlan
from backend.app.orchestration.workflows.preprocess import _build_preprocess_plan_failed_output


def test_preprocess_plan_validation_error_becomes_failed_output() -> None:
    try:
        PreprocessPlan.model_validate(
            {
                "operations": [
                    {"op": "scale", "columns": ["Mold_Temperature_12"]}
                ]
            }
        )
    except ValidationError as exc:
        result = _build_preprocess_plan_failed_output(exc)

    assert result["preprocess_result"]["status"] == "failed"
    assert result["preprocess_result"]["applied_ops_count"] == 0
    assert result["output"]["type"] == "preprocess_failed"
    assert "전처리 계획 형식" in result["output"]["content"]
```

**Run:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_preprocess_workflow_error_handling.py
```

Expected:

- fail because helper does not exist

---

### Task 4.2: preprocess planner failure helper 구현

**Objective:** 실패 payload 형태를 한 곳에서 만든다.

**Files:**

- Modify: `backend/app/orchestration/workflows/preprocess.py`
- Test: `backend/tests/test_preprocess_workflow_error_handling.py`

**구현 형태:**

```python
from pydantic import ValidationError


def _build_preprocess_plan_failed_output(exc: ValidationError) -> dict[str, Any]:
    message = "전처리 계획 형식이 올바르지 않습니다."
    return {
        "preprocess_result": {
            "status": "failed",
            "summary": message,
            "applied_ops_count": 0,
            "error": f"invalid preprocess plan: {exc}",
            "error_stage": "preprocess_plan",
        },
        "output": {
            "type": "preprocess_failed",
            "content": message,
        },
        "pending_approval": {},
        "approved_plan": {},
    }
```

**주의:**

- 사용자-facing content에는 너무 긴 Pydantic raw error를 넣지 않는다.
- raw detail은 `preprocess_result.error`에 둔다.
- `except Exception`은 쓰지 않는다.

**Run:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_preprocess_workflow_error_handling.py
```

Expected:

- pass

---

### Task 4.3: planner_node에서 ValidationError 처리

**Objective:** `build_preprocess_plan(...)` 실패 시 workflow가 approval_gate로 가지 않도록 한다.

**Files:**

- Modify: `backend/app/orchestration/workflows/preprocess.py`
- Test: `backend/tests/test_preprocess_workflow_error_handling.py`

**수정 위치:**

`planner_node(...)`

현재:

```python
plan = build_preprocess_plan(...)
return {
    "dataset_profile": dataset_profile,
    "preprocess_plan": plan.model_dump(),
}
```

수정 방향:

```python
try:
    plan = build_preprocess_plan(...)
except ValidationError as exc:
    failed = _build_preprocess_plan_failed_output(exc)
    failed["dataset_profile"] = dataset_profile
    return failed

return {
    "dataset_profile": dataset_profile,
    "preprocess_plan": plan.model_dump(),
}
```

**주의:**

- `ValidationError` import 필요
- LLM gateway에서 다른 API 오류가 난 경우까지 여기서 잡지 않는다.
- API/network 오류는 별도 error policy가 필요하면 나중에 다룬다.

---

### Task 4.4: planner 이후 conditional edge 추가

**Objective:** planner_node가 `preprocess_result.status=failed`를 반환하면 approval_gate를 건너뛰고 END로 종료한다.

**Files:**

- Modify: `backend/app/orchestration/workflows/preprocess.py`
- Test: workflow 또는 helper test 추가 가능

**현재 edge:**

```python
graph.add_edge("planner", "approval_gate")
```

**변경 방향:**

```python
def route_after_planner(state: PreprocessGraphState) -> str:
    result = state.get("preprocess_result") or {}
    if result.get("status") == "failed":
        return "failed"
    return "approval"
```

node 추가:

```python
def failed_node(_: PreprocessGraphState) -> Dict[str, Any]:
    return {}
```

edge 변경:

```python
graph.add_node("failed", failed_node)
graph.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "approval": "approval_gate",
        "failed": "failed",
    },
)
graph.add_edge("failed", END)
```

**주의:**

- main workflow의 `route_after_preprocess`는 이미 `preprocess_result.status == "failed"`를 처리한다.
- 따라서 main builder 수정은 필요 없을 가능성이 높다.

**Run:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_preprocess_workflow_error_handling.py
```

Expected:

- pass

---

### Commit 4

```bash
git add backend/app/orchestration/workflows/preprocess.py backend/tests/test_preprocess_workflow_error_handling.py
git commit -m "fix: 전처리 계획 검증 실패 상태 처리"
```

테스트를 따로 나누려면:

```bash
git add backend/tests/test_preprocess_workflow_error_handling.py
git commit -m "test: 전처리 계획 검증 실패 회귀 추가"

git add backend/app/orchestration/workflows/preprocess.py
git commit -m "fix: 전처리 계획 검증 실패 상태 처리"
```

---

## Phase 5. 문서 동기화 여부 확인

### Task 5.1: architecture 문서 변경 필요성 판단

**Objective:** workflow edge 또는 failure handling 변경이 현재 architecture 문서와 drift를 만드는지 확인한다.

**Files:**

- Check: `docs/architecture/request-lifecycle.md`
- Check: `docs/architecture/orchestration/workflows.md`
- Check: `docs/architecture/shared-state.md`

**판단 기준:**

문서 수정이 필요한 경우:

- preprocess subgraph edge 설명에 `planner -> approval_gate`만 고정적으로 설명되어 있다.
- preprocess planning 실패 상태가 문서에 없는 상태로 새로 추가된다.
- output payload key가 바뀐다.

문서 수정이 불필요할 수 있는 경우:

- 문서가 이미 “preprocess 실패 시 status_terminal” 정도로만 추상화되어 있다.
- public API shape가 바뀌지 않는다.
- state key가 새로 추가되지 않는다.

**예상:**

`preprocess_result.status="failed"`, `output.type="preprocess_failed"`는 이미 executor 실패에서 존재하는 계약이므로 `shared-state.md` 변경은 작을 가능성이 높다. 다만 preprocess planner 단계에서도 같은 실패 계약을 사용할 수 있다는 문구는 추가할 수 있다.

---

### Task 5.2: 필요한 경우 문서 최소 수정

**Objective:** 코드와 architecture 문서가 어긋나지 않게 한다.

**Files:**

- Modify if needed: `docs/architecture/request-lifecycle.md`
- Modify if needed: `docs/architecture/orchestration/workflows.md`

**수정 내용 예:**

```text
preprocess_flow에서 plan 생성 또는 실행 중 실패하면 preprocess_result.status="failed"와 output.type="preprocess_failed"를 남기고 main workflow의 status_terminal로 이동한다.
```

**Run:**

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```

Expected:

- pass

---

### Commit 5

문서 수정이 있으면:

```bash
git add docs/architecture/request-lifecycle.md docs/architecture/orchestration/workflows.md
git commit -m "docs: 전처리 실패 흐름 문서 정리"
```

문서 수정이 없으면 커밋하지 않는다.

---

## Phase 6. 통합 검증

### Task 6.1: 새 테스트 실행

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/test_planner_route_accuracy.py backend/tests/test_preprocess_plan_contract.py backend/tests/test_preprocess_workflow_error_handling.py
```

Expected:

- all passed

---

### Task 6.2: 기존 관련 테스트 실행

현재 AGENTS.md에는 아래 테스트가 언급되어 있지만, 현재 작업 트리에서는 해당 파일들이 존재하지 않는다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_analysis_planning_accuracy_guards.py backend/tests/test_planner_analysis_accuracy_guards.py
```

따라서 실제 존재하는 관련 테스트를 우선 실행한다.

Run:

```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/workflow/test_p0_moldset_workflow_contracts.py
PYTHONPATH=. pytest -q backend/tests/evaluation/runtime/test_p0_moldset_analysis_runtime.py
```

주의:

- `backend/tests/evaluation/runtime/test_p0_moldset_analysis_runtime.py`는 local benchmark raw dataset 유무에 따라 skip될 수 있다.
- skip은 실패가 아니다.

---

### Task 6.3: main workflow happy path 테스트 확인

AGENTS.md에는 아래 명령이 있다.

```bash
PYTHONPATH=. pytest -q backend/tests/test_main_workflow_analysis_happy_path.py
```

먼저 파일 존재 여부를 확인하고, 있으면 실행한다.

파일이 없으면 실행하지 않고 최종 보고에 “AGENTS에 언급되었지만 현재 트리에 없음”이라고 명시한다.

---

### Task 6.4: graphify update 실행

코드 파일을 수정했으므로 가능하면 실행한다.

Run:

```bash
graphify update .
```

주의:

- `graphify-out` 전체를 커밋 대상으로 삼지 않는다.
- 필요한 문서 변경만 커밋한다.

---

## 권장 커밋 분할

사용자 요청: 커밋 메시지는 `기능: 변경 내용` 형식으로 간단히 작성한다.

최근 git log는 `docs(benchmark): ...`, `test(benchmark): ...`, `fix(chat): ...`, `test: ...` 형태를 사용하지만, 이번에는 scope 없이 간단히 쓴다.

### Commit A

```text
test: 집계 시각화 질문 라우팅 회귀 추가
```

포함 파일:

- `backend/tests/test_planner_route_accuracy.py`

의미:

- 이번 trace의 root cause인 preprocess route 오판을 테스트로 고정한다.

---

### Commit B

```text
fix: 집계 시각화 질문 전처리 오판 방지
```

포함 파일:

- `backend/app/modules/planner/service.py`

의미:

- 명시적 전처리 요청이 없는 집계/시각화 질문은 preprocess_required=false로 보정한다.
- planner prompt에 관련 기준을 보강한다.

---

### Commit C

```text
test: 전처리 계획 scale 계약 추가
```

포함 파일:

- `backend/tests/test_preprocess_plan_contract.py`

의미:

- `scale` operation은 `method`가 있어야 한다는 contract를 테스트로 고정한다.

---

### Commit D

```text
fix: 전처리 계획 필수 필드 안내 강화
```

포함 파일:

- `backend/app/modules/preprocess/planner.py`

의미:

- preprocess planner LLM이 operation별 필수 필드를 빠뜨리지 않도록 prompt contract를 강화한다.

---

### Commit E

```text
test: 전처리 계획 검증 실패 회귀 추가
```

포함 파일:

- `backend/tests/test_preprocess_workflow_error_handling.py`

의미:

- `PreprocessPlan` 생성 단계의 validation failure가 raw exception으로 새지 않아야 함을 테스트한다.

---

### Commit F

```text
fix: 전처리 계획 검증 실패 상태 처리
```

포함 파일:

- `backend/app/orchestration/workflows/preprocess.py`

의미:

- preprocess plan validation 실패를 `preprocess_failed` 상태로 정리하고 approval_gate를 건너뛰게 한다.

---

### Commit G, 문서 수정이 필요한 경우만

```text
docs: 전처리 실패 흐름 문서 정리
```

포함 파일 후보:

- `docs/architecture/request-lifecycle.md`
- `docs/architecture/orchestration/workflows.md`
- `docs/architecture/shared-state.md`

의미:

- preprocess planning 실패도 preprocess 실패 계약으로 status_terminal에 연결된다는 문서 정리.

---

## 더 작은 커밋이 부담되면 최소 커밋 분할

시간이 부족하면 아래 3개로 줄일 수 있다.

### Commit 1

```text
fix: 집계 시각화 질문 전처리 오판 방지
```

포함:

- planner route test
- planner guard
- planner prompt 보강

### Commit 2

```text
fix: 전처리 계획 필수 필드 계약 강화
```

포함:

- preprocess plan contract test
- preprocess plan prompt 보강

### Commit 3

```text
fix: 전처리 계획 검증 실패 상태 처리
```

포함:

- preprocess workflow error handling test
- preprocess workflow validation failure handling
- 필요한 문서 변경

추천은 “권장 커밋 분할”이지만, 실제 PR 크기를 줄이고 싶으면 최소 커밋 분할도 가능하다.

---

## 최종 검증 명령

기본 검증:

```bash
PYTHONPATH=. pytest -q backend/tests/test_planner_route_accuracy.py backend/tests/test_preprocess_plan_contract.py backend/tests/test_preprocess_workflow_error_handling.py
```

관련 workflow/evaluation 검증:

```bash
PYTHONPATH=. pytest -q backend/tests/evaluation/workflow/test_p0_moldset_workflow_contracts.py
PYTHONPATH=. pytest -q backend/tests/evaluation/runtime/test_p0_moldset_analysis_runtime.py
```

문서 수정 시:

```bash
PYTHONPATH=. pytest -q backend/tests/test_architecture_docs.py backend/tests/test_docs_harness.py
```

프론트엔드 변경은 계획에 없으므로 `npm --prefix frontend run build`는 필수 검증이 아니다.

코드 파일 수정 후 가능하면:

```bash
graphify update .
```

---

## 완료 기준

이 작업은 아래가 모두 만족되면 완료다.

1. 같은 질문이 planner에서 `preprocess_required=false`, `need_visualization=true`로 처리된다.
2. 명시적 전처리 요청은 계속 preprocess 경로로 갈 수 있다.
3. preprocess planner prompt가 `scale.method` 등 operation별 필수 필드를 명확히 요구한다.
4. `PreprocessPlan` validation failure가 raw Pydantic error로 사용자에게 노출되지 않는다.
5. workflow 실패는 `preprocess_result.status="failed"`, `output.type="preprocess_failed"`로 정리된다.
6. 관련 테스트가 통과한다.
7. architecture 문서가 코드와 drift되지 않는다.

---

## 이번 문제에 대한 기대 동작

Before:

```text
질문
-> planner: preprocess_required=true
-> preprocess_flow
-> EDA recommendation
-> scale operation method 누락
-> Pydantic ValidationError
-> Analysis Failed
```

After:

```text
질문
-> planner: preprocess_required=false, need_visualization=true
-> analysis_flow
-> visualization_flow
-> PassOrFail 비율 / Reason별 건수 / 제품별 생산량 차트 생성
-> 정상 응답
```

진짜 전처리 질문일 때:

```text
질문: 수치형 컬럼을 표준화한 뒤 분석해줘
-> planner: preprocess_required=true
-> preprocess_flow
-> scale operation 생성: method="standardize"
-> approval card
-> 승인 후 분석
```

plan 생성이 또 깨질 때:

```text
-> raw Pydantic error 노출 X
-> preprocess_failed 상태로 정리
-> trace에서 preprocess_plan validation 원인 확인 가능
```
