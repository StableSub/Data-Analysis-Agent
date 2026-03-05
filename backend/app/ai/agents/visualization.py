"""
V1 시각화 서브그래프.

역할:
- 선택된 데이터셋에서 시각화 계획을 생성한다.
- 계획된 파이썬 코드를 샌드박스 실행해 PNG를 생성한다.
- 최종 output은 생성하지 않고 상태만 누적한다.
"""

from __future__ import annotations

import base64
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Literal

import pandas as pd
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.ai.agents.state import VisualizationGraphState
from backend.app.ai.agents.utils import call_structured_llm, resolve_target_source_id
from backend.app.domain.data_source.repository import DataSourceRepository

PYTHON_EXECUTABLE = "/Users/anjeongseob/.virtualenvs/ai_agent/bin/python"
SCRIPT_TIMEOUT_SECONDS = 15
MAX_SAMPLE_ROWS = 2000
MAX_POINTS = 120

CHART_KEYWORDS: dict[str, tuple[str, ...]] = {
    "scatter": ("scatter", "산점도", "점그래프"),
    "line": ("line", "라인", "선그래프", "시계열"),
    "bar": ("bar", "막대"),
    "hist": ("hist", "histogram", "히스토그램"),
    "box": ("box", "boxplot", "박스플롯"),
}


class ChartSelection(BaseModel):
    chart_type: Literal["scatter", "line", "bar", "hist", "box"] = Field(...)
    x_column: str = Field(...)
    y_column: str = Field(default="")
    reason: str = Field(default="")


def _detect_requested_chart_type(query: str) -> str | None:
    """
    역할: 사용자 질의 텍스트에서 차트 타입 키워드를 탐지해 요청 유형을 추정한다.
    입력: 자연어 질의 문자열(`query`)을 받는다.
    출력: 감지된 차트 타입(`scatter/line/bar/hist/box`) 또는 `None`을 반환한다.
    데코레이터: 없음.
    호출 맥락: 시각화 planner에서 LLM 선택 실패 시 규칙 기반 폴백의 시작점으로 사용된다.
    """
    lowered = query.lower()
    for chart_type, keywords in CHART_KEYWORDS.items():
        for keyword in keywords:
            if keyword.isascii():
                if keyword in lowered:
                    return chart_type
                continue
            if keyword in query:
                return chart_type
    return None


def _infer_datetime_columns(df: pd.DataFrame) -> list[str]:
    """
    역할: 데이터프레임에서 datetime 타입 또는 날짜/시간 형식으로 해석 가능한 컬럼을 추론한다.
    입력: 샘플링된 데이터프레임(`df`)을 받는다.
    출력: datetime으로 사용할 수 있는 컬럼명 문자열 리스트를 반환한다.
    데코레이터: 없음.
    호출 맥락: profile 정보가 없을 때 planner의 규칙 기반 컬럼 분류 단계에서 사용된다.
    """
    datetime_columns = [
        str(col)
        for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns.tolist()
    ]
    for col in df.columns:
        col_name = str(col)
        if col_name in datetime_columns:
            continue
        lowered = col_name.lower()
        if "date" not in lowered and "time" not in lowered:
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        parsed_ratio = float(parsed.notna().mean()) if len(parsed) > 0 else 0.0
        if parsed_ratio >= 0.7:
            datetime_columns.append(col_name)
    return datetime_columns


def _select_chart(
    *,
    requested_chart_type: str | None,
    numeric_columns: list[str],
    datetime_columns: list[str],
    categorical_columns: list[str],
) -> Dict[str, Any]:
    """
    역할: 요청 차트 타입과 컬럼 집합을 기준으로 규칙 기반 시각화 계획을 선택한다.
    입력: 요청 타입(`requested_chart_type`)과 numeric/datetime/categorical 컬럼 리스트를 받는다.
    출력: 계획 가능 여부, 선택 축, 이유를 담은 표준 plan 딕셔너리를 반환한다.
    데코레이터: 없음.
    호출 맥락: LLM 차트 선택이 실패했을 때 안정적인 폴백 경로로 실행된다.
    """
    mode = "specified" if requested_chart_type else "auto"
    chart_type = requested_chart_type or ""
    x_key = ""
    y_key = ""
    reason = ""
    x_is_datetime = False

    if requested_chart_type == "scatter":
        if len(numeric_columns) >= 2:
            chart_type = "scatter"
            x_key, y_key = numeric_columns[0], numeric_columns[1]
            reason = "사용자가 산점도를 요청해 수치형 2개 컬럼을 선택했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "scatter",
                "x_key": "",
                "y_key": "",
                "reason": "산점도 요청이 있었지만 수치형 컬럼이 2개 미만입니다.",
                "x_is_datetime": False,
            }
    elif requested_chart_type == "line":
        if datetime_columns and numeric_columns:
            chart_type = "line"
            x_key, y_key = datetime_columns[0], numeric_columns[0]
            x_is_datetime = True
            reason = "사용자가 라인 차트를 요청해 datetime+numeric 조합을 선택했습니다."
        elif len(numeric_columns) >= 2:
            chart_type = "line"
            x_key, y_key = numeric_columns[0], numeric_columns[1]
            reason = "시간 컬럼이 없어 수치형 2개 컬럼으로 라인 차트를 구성했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "line",
                "x_key": "",
                "y_key": "",
                "reason": "라인 차트 요청이 있었지만 사용할 컬럼 조합이 없습니다.",
                "x_is_datetime": False,
            }
    elif requested_chart_type == "bar":
        if categorical_columns and numeric_columns:
            chart_type = "bar"
            x_key, y_key = categorical_columns[0], numeric_columns[0]
            reason = "사용자가 막대 차트를 요청해 categorical+numeric 조합을 선택했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "bar",
                "x_key": "",
                "y_key": "",
                "reason": "막대 차트 요청이 있었지만 categorical+numeric 조합이 없습니다.",
                "x_is_datetime": False,
            }
    elif requested_chart_type == "hist":
        if numeric_columns:
            chart_type = "hist"
            x_key, y_key = numeric_columns[0], ""
            reason = "사용자가 히스토그램을 요청해 수치형 컬럼 1개를 선택했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "hist",
                "x_key": "",
                "y_key": "",
                "reason": "히스토그램 요청이 있었지만 수치형 컬럼이 없습니다.",
                "x_is_datetime": False,
            }
    elif requested_chart_type == "box":
        if categorical_columns and numeric_columns:
            chart_type = "box"
            x_key, y_key = categorical_columns[0], numeric_columns[0]
            reason = "사용자가 박스플롯을 요청해 categorical+numeric 조합을 선택했습니다."
        elif numeric_columns:
            chart_type = "box"
            x_key, y_key = "", numeric_columns[0]
            reason = "사용자가 박스플롯을 요청해 수치형 컬럼 1개를 선택했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "box",
                "x_key": "",
                "y_key": "",
                "reason": "박스플롯 요청이 있었지만 수치형 컬럼이 없습니다.",
                "x_is_datetime": False,
            }
    else:
        if datetime_columns and numeric_columns:
            chart_type = "line"
            x_key, y_key = datetime_columns[0], numeric_columns[0]
            x_is_datetime = True
            reason = "datetime+numeric 조합을 감지해 line 차트를 자동 선택했습니다."
        elif len(numeric_columns) >= 2:
            chart_type = "scatter"
            x_key, y_key = numeric_columns[0], numeric_columns[1]
            reason = "수치형 컬럼 2개 이상이라 scatter 차트를 자동 선택했습니다."
        elif len(numeric_columns) == 1:
            chart_type = "hist"
            x_key, y_key = numeric_columns[0], ""
            reason = "수치형 컬럼이 1개라 histogram 차트를 자동 선택했습니다."
        elif categorical_columns and numeric_columns:
            chart_type = "bar"
            x_key, y_key = categorical_columns[0], numeric_columns[0]
            reason = "categorical+numeric 조합을 감지해 bar 차트를 자동 선택했습니다."
        else:
            return {
                "status": "unavailable",
                "mode": mode,
                "chart_type": "",
                "x_key": "",
                "y_key": "",
                "reason": "시각화에 사용할 컬럼 조합을 찾지 못했습니다.",
                "x_is_datetime": False,
            }

    return {
        "status": "planned",
        "mode": mode,
        "chart_type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "reason": reason,
        "x_is_datetime": x_is_datetime,
    }


def _select_chart_with_llm(
    *,
    query: str,
    numeric_columns: list[str],
    datetime_columns: list[str],
    categorical_columns: list[str],
    model_id: str | None,
    default_model: str,
) -> Dict[str, Any] | None:
    """
    역할: 질문 의미와 컬럼 타입 정보를 함께 사용해 LLM 기반 차트/축 선택을 수행한다.
    입력: 사용자 질의, 컬럼 분류 리스트, 모델 식별자(`model_id`, `default_model`)를 받는다.
    출력: 유효한 선택이면 `planned` plan 딕셔너리, 검증 실패 시 `None`을 반환한다.
    데코레이터: 없음.
    호출 맥락: visualization planner의 1차 선택기로 사용되고 실패 시 `_select_chart`로 폴백된다.
    """
    columns_info = (
        f"numeric: {numeric_columns}\n"
        f"datetime: {datetime_columns}\n"
        f"categorical: {categorical_columns}"
    )
    result = call_structured_llm(
        schema=ChartSelection,
        system_prompt=(
            "사용자 질문과 컬럼 목록을 보고 가장 적합한 차트를 선택하라. "
            "x_column, y_column은 반드시 주어진 컬럼 목록에서 선택하라. "
            "hist는 y_column이 빈 문자열이다."
        ),
        human_prompt=f"query: {query}\n\n{columns_info}",
        model_id=model_id,
        default_model=default_model,
    )
    dump = result.model_dump()
    all_columns = numeric_columns + datetime_columns + categorical_columns
    x_column = str(dump.get("x_column") or "")
    y_column = str(dump.get("y_column") or "")
    if x_column not in all_columns:
        return None
    if y_column and y_column not in all_columns:
        return None
    chart_type = str(dump.get("chart_type") or "")
    return {
        "status": "planned",
        "mode": "llm",
        "chart_type": chart_type,
        "x_key": x_column,
        "y_key": y_column,
        "reason": str(dump.get("reason") or ""),
        "x_is_datetime": x_column in datetime_columns,
    }


def _build_python_code(
    *,
    dataset_path: str,
    chart_type: str,
    x_key: str,
    y_key: str,
    output_filename: str,
    max_points: int,
    x_is_datetime: bool,
) -> str:
    """
    역할: 선택된 차트 계획을 실제 matplotlib 실행 스크립트 문자열로 변환한다.
    입력: 데이터 경로, 차트 타입, 축 컬럼, 출력 파일명, 포인트 제한, datetime 축 여부를 받는다.
    출력: 별도 프로세스에서 실행 가능한 Python 코드 문자열을 반환한다.
    데코레이터: 없음.
    호출 맥락: planner 노드가 executor에 전달할 `python_code`를 생성할 때 호출된다.
    """
    header = (
        "from pathlib import Path\n"
        "import pandas as pd\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n\n"
        f"dataset_path = Path({dataset_path!r})\n"
        f"output_path = Path(__file__).resolve().parent / {output_filename!r}\n"
        f"max_points = {max_points}\n\n"
        "df = pd.read_csv(dataset_path)\n"
        "plt.figure(figsize=(8, 5))\n"
    )

    if chart_type == "scatter":
        body = (
            f"data = df[[{x_key!r}, {y_key!r}]].dropna().head(max_points)\n"
            f"plt.scatter(data[{x_key!r}], data[{y_key!r}], alpha=0.7, s=25)\n"
            f"plt.xlabel({x_key!r})\n"
            f"plt.ylabel({y_key!r})\n"
            f"plt.title({f'Scatter: {x_key} vs {y_key}'!r})\n"
        )
    elif chart_type == "line":
        if x_is_datetime:
            body = (
                f"data = df[[{x_key!r}, {y_key!r}]].dropna().copy()\n"
                f"data[{x_key!r}] = pd.to_datetime(data[{x_key!r}], errors='coerce')\n"
                f"data = data.dropna().sort_values({x_key!r}).head(max_points)\n"
                f"plt.plot(data[{x_key!r}], data[{y_key!r}], linewidth=1.8)\n"
            )
        else:
            body = (
                f"data = df[[{x_key!r}, {y_key!r}]].dropna().head(max_points)\n"
                f"plt.plot(data[{x_key!r}], data[{y_key!r}], linewidth=1.8)\n"
            )
        body += (
            f"plt.xlabel({x_key!r})\n"
            f"plt.ylabel({y_key!r})\n"
            f"plt.title({f'Line: {x_key} vs {y_key}'!r})\n"
        )
    elif chart_type == "hist":
        body = (
            f"series = df[{x_key!r}].dropna().head(max_points)\n"
            "plt.hist(series, bins=20, edgecolor='white')\n"
            f"plt.xlabel({x_key!r})\n"
            "plt.ylabel('count')\n"
            f"plt.title({f'Histogram: {x_key}'!r})\n"
        )
    elif chart_type == "bar":
        body = (
            f"data = df[[{x_key!r}, {y_key!r}]].dropna().copy()\n"
            f"data[{x_key!r}] = data[{x_key!r}].astype(str)\n"
            f"grouped = data.groupby({x_key!r}, as_index=False)[{y_key!r}].mean().head(20)\n"
            f"plt.bar(grouped[{x_key!r}], grouped[{y_key!r}])\n"
            f"plt.xlabel({x_key!r})\n"
            f"plt.ylabel({y_key!r})\n"
            f"plt.title({f'Bar(mean): {x_key} vs {y_key}'!r})\n"
            "plt.xticks(rotation=45, ha='right')\n"
        )
    else:
        if x_key:
            body = (
                f"data = df[[{x_key!r}, {y_key!r}]].dropna().copy()\n"
                f"data[{x_key!r}] = data[{x_key!r}].astype(str)\n"
                "labels = []\n"
                "groups = []\n"
                f"for label, group in data.groupby({x_key!r}):\n"
                "    labels.append(label)\n"
                f"    groups.append(group[{y_key!r}].values)\n"
                "labels = labels[:20]\n"
                "groups = groups[:20]\n"
                "plt.boxplot(groups, labels=labels, showfliers=True)\n"
                "plt.xticks(rotation=45, ha='right')\n"
                f"plt.ylabel({y_key!r})\n"
                f"plt.title({f'Boxplot: {y_key} by {x_key}'!r})\n"
            )
        else:
            body = (
                f"series = df[{y_key!r}].dropna().head(max_points)\n"
                "plt.boxplot(series.values, showfliers=True)\n"
                f"plt.ylabel({y_key!r})\n"
                f"plt.title({f'Boxplot: {y_key}'!r})\n"
            )

    footer = (
        "plt.tight_layout()\n"
        "plt.savefig(output_path, dpi=150)\n"
    )
    return header + body + footer


def _chart_has_data(
    *,
    df: pd.DataFrame,
    chart_type: str,
    x_key: str,
    y_key: str,
    x_is_datetime: bool,
) -> bool:
    """
    역할: 선택된 차트/축 조합에서 실제 시각화 가능한 유효 데이터가 존재하는지 검증한다.
    입력: 샘플 데이터프레임과 차트 타입, x/y 키, datetime 축 여부를 받는다.
    출력: 유효 데이터가 있으면 `True`, 없으면 `False`를 반환한다.
    데코레이터: 없음.
    호출 맥락: executor 단계에서 스크립트 실행 전 최종 가드로 사용되어 무의미한 렌더링을 차단한다.
    """
    if chart_type in {"scatter", "line"} and x_key and y_key:
        sample = df[[x_key, y_key]].dropna().copy()
        if chart_type == "line" and x_is_datetime:
            sample[x_key] = pd.to_datetime(sample[x_key], errors="coerce")
            sample = sample.dropna()
        return not sample.empty
    if chart_type == "hist" and x_key:
        return not df[x_key].dropna().empty
    if chart_type == "bar" and x_key and y_key:
        sample = df[[x_key, y_key]].dropna()
        return not sample.empty
    if chart_type == "box" and y_key:
        if x_key:
            sample = df[[x_key, y_key]].dropna()
            return not sample.empty
        return not df[y_key].dropna().empty
    return False


def _run_chart_script(script_path: Path) -> Dict[str, Any]:
    """
    역할: 생성된 차트 렌더링 스크립트를 별도 파이썬 프로세스로 실행하고 결과를 수집한다.
    입력: 실행할 스크립트 경로(`script_path`)를 받는다.
    출력: 타임아웃 여부, 리턴코드, stdout/stderr를 포함한 실행 결과 딕셔너리를 반환한다.
    데코레이터: 없음.
    호출 맥락: visualization executor에서 실제 PNG 아티팩트 생성을 트리거하는 런처로 사용된다.
    """
    process = subprocess.Popen(
        [PYTHON_EXECUTABLE, str(script_path)],
        cwd=str(script_path.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    deadline = time.monotonic() + SCRIPT_TIMEOUT_SECONDS
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)

    if process.poll() is None:
        process.kill()
        stdout, stderr = process.communicate()
        return {
            "timed_out": True,
            "returncode": -1,
            "stdout": stdout,
            "stderr": stderr,
        }

    stdout, stderr = process.communicate()
    return {
        "timed_out": False,
        "returncode": int(process.returncode or 0),
        "stdout": stdout,
        "stderr": stderr,
    }


def build_visualization_workflow(*, db: Session, default_model: str = "gpt-5-nano"):
    """
    역할: 시각화 계획 수립과 코드 실행을 담당하는 2단계(Planner/Executor) 서브그래프를 생성한다.
    입력: 데이터 조회용 DB 세션(`db`)과 LLM 계획 기본 모델명(`default_model`)을 받는다.
    출력: `visualization_plan`과 `visualization_result`를 누적하는 컴파일된 그래프를 반환한다.
    데코레이터: 없음.
    호출 맥락: 메인 워크플로우에서 `ask_visualization` 요청이 감지된 경로에 삽입되어 실행된다.
    """
    data_source_repository = DataSourceRepository(db)

    def visualization_planner_node(state: VisualizationGraphState) -> Dict[str, Any]:
        """
        역할: 대상 데이터셋과 컬럼 정보를 바탕으로 차트 유형, 축, 실행 코드를 포함한 계획을 생성한다.
        입력: `state.user_input`, `state.dataset_profile`, source 식별 정보, 모델 ID를 포함한 상태를 받는다.
        출력: 실행 가능하면 `visualization_plan(status=planned)`, 아니면 사유 포함 `unavailable` 계획을 반환한다.
        데코레이터: 없음.
        호출 맥락: visualization 서브그래프 첫 노드로 executor가 사용할 실행 계획을 확정한다.
        """
        source_id = resolve_target_source_id(state)
        query = str(state.get("user_input", "")).strip()
        requested_chart_type = _detect_requested_chart_type(query)
        mode = "specified" if requested_chart_type else "auto"

        empty_plan = {
            "status": "unavailable",
            "source_id": source_id or "",
            "mode": mode,
            "chart_type": requested_chart_type or "",
            "x_key": "",
            "y_key": "",
            "reason": "",
            "python_code": "",
            "output_filename": "",
        }

        if not source_id:
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": "시각화 대상 source_id가 없어 계획을 생성하지 못했습니다.",
                }
            }

        dataset = data_source_repository.get_by_source_id(source_id)
        if dataset is None or not dataset.storage_path:
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": "시각화 대상 데이터셋을 찾지 못했습니다.",
                }
            }

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": "데이터 파일이 없어 시각화 계획을 생성하지 못했습니다.",
                }
            }

        numeric_columns: list[str] = []
        datetime_columns: list[str] = []
        categorical_columns: list[str] = []
        profile = state.get("dataset_profile")
        profile_dict = profile if isinstance(profile, dict) else {}
        has_profile_columns = (
            bool(profile_dict.get("available"))
            and isinstance(profile_dict.get("numeric_columns"), list)
            and isinstance(profile_dict.get("datetime_columns"), list)
            and isinstance(profile_dict.get("categorical_columns"), list)
        )
        if has_profile_columns:
            numeric_columns = [str(col) for col in profile_dict.get("numeric_columns", [])]
            datetime_columns = [str(col) for col in profile_dict.get("datetime_columns", [])]
            categorical_columns = [str(col) for col in profile_dict.get("categorical_columns", [])]
        else:
            df = pd.read_csv(file_path, nrows=MAX_SAMPLE_ROWS)
            if df.empty:
                return {
                    "visualization_plan": {
                        **empty_plan,
                        "reason": "데이터가 비어 있어 시각화 계획을 생성하지 못했습니다.",
                    }
                }
            numeric_columns = [
                str(col) for col in df.select_dtypes(include="number").columns.tolist()
            ]
            datetime_columns = _infer_datetime_columns(df)
            datetime_set = set(datetime_columns)
            numeric_set = set(numeric_columns)
            categorical_columns = [
                str(col)
                for col in df.columns
                if str(col) not in datetime_set and str(col) not in numeric_set
            ]

        selection = _select_chart_with_llm(
            query=query,
            numeric_columns=numeric_columns,
            datetime_columns=datetime_columns,
            categorical_columns=categorical_columns,
            model_id=state.get("model_id"),
            default_model=default_model,
        )
        if selection is None:
            selection = _select_chart(
                requested_chart_type=requested_chart_type,
                numeric_columns=numeric_columns,
                datetime_columns=datetime_columns,
                categorical_columns=categorical_columns,
            )
        if selection["status"] != "planned":
            return {
                "visualization_plan": {
                    **empty_plan,
                    "reason": selection["reason"],
                }
            }

        chart_type = str(selection["chart_type"])
        x_key = str(selection["x_key"])
        y_key = str(selection["y_key"])
        x_is_datetime = bool(selection["x_is_datetime"])

        output_filename = f"viz_{chart_type}.png"
        python_code = _build_python_code(
            dataset_path=str(file_path),
            chart_type=chart_type,
            x_key=x_key,
            y_key=y_key,
            output_filename=output_filename,
            max_points=MAX_POINTS,
            x_is_datetime=x_is_datetime,
        )
        plan = {
            "status": "planned",
            "source_id": source_id,
            "mode": str(selection["mode"]),
            "chart_type": chart_type,
            "x_key": x_key,
            "y_key": y_key,
            "reason": str(selection["reason"]),
            "python_code": python_code,
            "output_filename": output_filename,
            "x_is_datetime": x_is_datetime,
        }
        return {"visualization_plan": plan}

    def visualization_executor_node(state: VisualizationGraphState) -> Dict[str, Any]:
        """
        역할: planner가 만든 코드를 샌드박스 프로세스로 실행해 PNG 아티팩트를 생성하고 결과를 상태에 기록한다.
        입력: `state.visualization_plan`과 대상 데이터셋 경로를 포함한 시각화 상태를 받는다.
        출력: 성공 시 chart/artifact를 포함한 `visualization_result(generated)`, 실패 시 `unavailable`을 반환한다.
        데코레이터: 없음.
        호출 맥락: planner 다음 노드로 연결되며 시각화 경로의 최종 산출물을 만드는 실행 단계다.
        """
        plan = state.get("visualization_plan")
        plan_dict = plan if isinstance(plan, dict) else {}
        status = plan_dict.get("status")
        source_id = str(plan_dict.get("source_id") or "")
        chart_type = str(plan_dict.get("chart_type") or "")
        x_key = str(plan_dict.get("x_key") or "")
        y_key = str(plan_dict.get("y_key") or "")
        reason = str(plan_dict.get("reason") or "")
        python_code = str(plan_dict.get("python_code") or "")
        output_filename = str(plan_dict.get("output_filename") or "")
        x_is_datetime = bool(plan_dict.get("x_is_datetime", False))

        if status != "planned":
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": reason or "시각화 계획이 없어 실행을 생략했습니다.",
                }
            }

        if not python_code or not output_filename or not chart_type:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "시각화 실행 코드가 없어 차트를 생성하지 못했습니다.",
                }
            }

        dataset = data_source_repository.get_by_source_id(source_id) if source_id else None
        if dataset is None or not dataset.storage_path:
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "시각화 대상 데이터셋을 찾지 못했습니다.",
                }
            }
        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "데이터 파일이 없어 차트를 생성하지 못했습니다.",
                }
            }
        df = pd.read_csv(file_path, nrows=MAX_SAMPLE_ROWS)
        if df.empty or not _chart_has_data(
            df=df,
            chart_type=chart_type,
            x_key=x_key,
            y_key=y_key,
            x_is_datetime=x_is_datetime,
        ):
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "선택된 컬럼에서 유효한 시각화 데이터가 없습니다.",
                }
            }

        temp_dir = Path(tempfile.mkdtemp(prefix="viz_exec_"))
        script_path = temp_dir / "render_chart.py"
        output_path = temp_dir / output_filename
        script_path.write_text(python_code, encoding="utf-8")

        run_result = _run_chart_script(script_path)
        if bool(run_result.get("timed_out", False)):
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": "시각화 코드 실행 시간이 초과되어 차트를 생성하지 못했습니다.",
                }
            }

        if int(run_result.get("returncode", 1)) != 0 or not output_path.exists():
            stderr_text = str(run_result.get("stderr") or "").strip()
            error_message = stderr_text.splitlines()[-1] if stderr_text else "시각화 코드 실행에 실패했습니다."
            return {
                "visualization_result": {
                    "status": "unavailable",
                    "source_id": source_id,
                    "summary": f"시각화 코드 실행 실패: {error_message}",
                }
            }

        image_base64 = base64.b64encode(output_path.read_bytes()).decode("ascii")
        axis_text = f"{x_key} vs {y_key}" if x_key and y_key else (x_key or y_key or "-")

        return {
            "visualization_result": {
                "status": "generated",
                "source_id": source_id,
                "summary": f"{axis_text} 기준으로 {chart_type} 차트를 생성했습니다.",
                "chart": {
                    "chart_type": chart_type,
                    "x_key": x_key,
                    "y_key": y_key,
                },
                "artifact": {
                    "mime_type": "image/png",
                    "image_base64": image_base64,
                    "code": python_code,
                },
            }
        }

    graph = StateGraph(VisualizationGraphState)
    graph.add_node("visualization_planner", visualization_planner_node)
    graph.add_node("visualization_executor", visualization_executor_node)
    graph.add_edge(START, "visualization_planner")
    graph.add_edge("visualization_planner", "visualization_executor")
    graph.add_edge("visualization_executor", END)

    return graph.compile()
