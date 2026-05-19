from __future__ import annotations

import base64
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from .planner import VisualizationPlan
from .service import VisualizationService

SCRIPT_TIMEOUT_SECONDS = 15


def execute_visualization_plan(
    *,
    visualization_service: VisualizationService,
    visualization_plan: dict[str, Any] | None,
    approved_plan: dict[str, Any] | None,
    max_sample_rows: int,
    max_points: int,
) -> dict[str, Any]:
    try:
        plan = VisualizationPlan.model_validate(approved_plan or visualization_plan or {})
    except ValidationError as exc:
        return _build_unavailable_result(
            source_id="",
            summary=f"시각화 계획 형식이 올바르지 않습니다: {exc}",
        )

    source_id = str(plan.source_id or "")
    if plan.status != "planned":
        return _build_unavailable_result(
            source_id=source_id,
            summary=plan.reason or "시각화 계획이 없어 실행을 생략했습니다.",
        )

    if not source_id or not plan.chart_type:
        return _build_unavailable_result(
            source_id=source_id,
            summary="시각화 대상 정보가 부족해 차트를 생성하지 못했습니다.",
        )

    df, load_status = visualization_service.load_sample_frame(source_id, nrows=max_sample_rows)
    if load_status == "dataset_missing":
        return _build_unavailable_result(
            source_id=source_id,
            summary="시각화 대상 데이터셋을 찾지 못했습니다.",
        )
    if load_status == "unsupported_format":
        return _build_unavailable_result(
            source_id=source_id,
            summary="CSV 형식 데이터셋만 시각화할 수 있습니다.",
        )
    if load_status == "read_error":
        return _build_unavailable_result(
            source_id=source_id,
            summary="데이터를 읽지 못해 차트를 생성하지 못했습니다.",
        )

    if df.empty or not _chart_has_data(
        df=df,
        chart_type=plan.chart_type,
        x_key=plan.x_key,
        y_key=plan.y_key,
        x_is_datetime=plan.x_is_datetime,
    ):
        return _build_unavailable_result(
            source_id=source_id,
            summary="선택된 컬럼에서 유효한 시각화 데이터가 없습니다.",
        )

    dataset_path = visualization_service.resolve_source_path(source_id)
    if dataset_path is None:
        return _build_unavailable_result(
            source_id=source_id,
            summary="시각화 대상 데이터셋을 찾지 못했습니다.",
        )

    output_filename = f"viz_{plan.chart_type}.png"
    python_code = _build_python_code(
        dataset_path=str(dataset_path),
        chart_type=plan.chart_type,
        x_key=plan.x_key,
        y_key=plan.y_key,
        output_filename=output_filename,
        max_points=max_points,
        x_is_datetime=plan.x_is_datetime,
    )

    with tempfile.TemporaryDirectory(prefix="viz_exec_") as temp_dir:
        temp_path = Path(temp_dir)
        script_path = temp_path / "render_chart.py"
        output_path = temp_path / output_filename
        script_path.write_text(python_code, encoding="utf-8")

        run_result = _run_chart_script(script_path)
        if bool(run_result.get("timed_out", False)):
            return _build_unavailable_result(
                source_id=source_id,
                summary="시각화 코드 실행 시간이 초과되어 차트를 생성하지 못했습니다.",
            )

        if int(run_result.get("returncode", 1)) != 0 or not output_path.exists():
            stderr_text = str(run_result.get("stderr") or "").strip()
            error_message = (
                stderr_text.splitlines()[-1]
                if stderr_text
                else "시각화 코드 실행에 실패했습니다."
            )
            return _build_unavailable_result(
                source_id=source_id,
                summary=f"시각화 코드 실행 실패: {error_message}",
            )

        image_base64 = base64.b64encode(output_path.read_bytes()).decode("ascii")
        axis_text = (
            f"{plan.x_key} vs {plan.y_key}"
            if plan.x_key and plan.y_key
            else (plan.x_key or plan.y_key or "-")
        )
        return {
            "status": "generated",
            "source_id": source_id,
            "summary": f"{axis_text} 기준으로 {plan.chart_type} 차트를 생성했습니다.",
            "chart": {
                "chart_type": plan.chart_type,
                "x_key": plan.x_key,
                "y_key": plan.y_key,
            },
            "charts": [],
            "artifact": {
                "mime_type": "image/png",
                "image_base64": image_base64,
                "code": python_code,
            },
        }


def _build_unavailable_result(*, source_id: str, summary: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source_id": source_id,
        "summary": summary,
    }


def _chart_has_data(
    *,
    df: pd.DataFrame,
    chart_type: str,
    x_key: str,
    y_key: str,
    x_is_datetime: bool,
) -> bool:
    if chart_type in {"scatter", "line"} and x_key and y_key:
        sample = df[[x_key, y_key]].dropna().copy()
        if chart_type == "line" and x_is_datetime:
            sample[x_key] = pd.to_datetime(sample[x_key], errors="coerce")
            sample = sample.dropna()
        return not sample.empty
    if chart_type == "hist" and x_key:
        return not df[x_key].dropna().empty
    if chart_type == "bar" and x_key and y_key:
        return not df[[x_key, y_key]].dropna().empty
    if chart_type == "box" and y_key:
        if x_key:
            return not df[[x_key, y_key]].dropna().empty
        return not df[y_key].dropna().empty
    return False


def _run_chart_script(script_path: Path) -> dict[str, Any]:
    process = subprocess.Popen(
        [sys.executable, str(script_path)],
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
    header = (
        "from pathlib import Path\n"
        "import pandas as pd\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n\n"
        "plt.style.use('default')\n"
        f"dataset_path = Path({dataset_path!r})\n"
        f"output_path = Path(__file__).resolve().parent / {output_filename!r}\n"
        f"max_points = {max_points}\n\n"
        "df = pd.read_csv(dataset_path)\n"
        "fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')\n"
        "ax.set_facecolor('white')\n"
    )

    if chart_type == "scatter":
        body = (
            f"data = df[[{x_key!r}, {y_key!r}]].dropna().head(max_points)\n"
            f"ax.scatter(data[{x_key!r}], data[{y_key!r}], alpha=0.7, s=25, color='#2563EB')\n"
            f"ax.set_xlabel({x_key!r})\n"
            f"ax.set_ylabel({y_key!r})\n"
            f"ax.set_title({f'Scatter: {x_key} vs {y_key}'!r})\n"
        )
    elif chart_type == "line":
        if x_is_datetime:
            body = (
                f"data = df[[{x_key!r}, {y_key!r}]].dropna().copy()\n"
                f"data[{x_key!r}] = pd.to_datetime(data[{x_key!r}], errors='coerce')\n"
                f"data = data.dropna().sort_values({x_key!r}).head(max_points)\n"
                f"ax.plot(data[{x_key!r}], data[{y_key!r}], linewidth=1.8, color='#2563EB')\n"
            )
        else:
            body = (
                f"data = df[[{x_key!r}, {y_key!r}]].dropna().head(max_points)\n"
                f"ax.plot(data[{x_key!r}], data[{y_key!r}], linewidth=1.8, color='#2563EB')\n"
            )
        body += (
            f"ax.set_xlabel({x_key!r})\n"
            f"ax.set_ylabel({y_key!r})\n"
            f"ax.set_title({f'Line: {x_key} vs {y_key}'!r})\n"
        )
    elif chart_type == "hist":
        body = (
            f"series = df[{x_key!r}].dropna().head(max_points)\n"
            "ax.hist(series, bins=20, edgecolor='white', color='#2563EB')\n"
            f"ax.set_xlabel({x_key!r})\n"
            "ax.set_ylabel('count')\n"
            f"ax.set_title({f'Histogram: {x_key}'!r})\n"
        )
    elif chart_type == "bar":
        body = (
            f"data = df[[{x_key!r}, {y_key!r}]].dropna().copy()\n"
            f"data[{x_key!r}] = data[{x_key!r}].astype(str)\n"
            f"grouped = data.groupby({x_key!r}, as_index=False)[{y_key!r}].mean().head(20)\n"
            f"ax.bar(grouped[{x_key!r}], grouped[{y_key!r}], color='#2563EB')\n"
            f"ax.set_xlabel({x_key!r})\n"
            f"ax.set_ylabel({y_key!r})\n"
            f"ax.set_title({f'Bar(mean): {x_key} vs {y_key}'!r})\n"
            "ax.tick_params(axis='x', rotation=45)\n"
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
                "ax.boxplot(groups, labels=labels, showfliers=True)\n"
                "ax.tick_params(axis='x', rotation=45)\n"
                f"ax.set_ylabel({y_key!r})\n"
                f"ax.set_title({f'Boxplot: {y_key} by {x_key}'!r})\n"
            )
        else:
            body = (
                f"series = df[{y_key!r}].dropna().head(max_points)\n"
                "ax.boxplot(series.values, showfliers=True)\n"
                f"ax.set_ylabel({y_key!r})\n"
                f"ax.set_title({f'Boxplot: {y_key}'!r})\n"
            )

    footer = (
        "fig.patch.set_facecolor('white')\n"
        "ax.set_facecolor('white')\n"
        "ax.tick_params(colors='#111827')\n"
        "ax.xaxis.label.set_color('#111827')\n"
        "ax.yaxis.label.set_color('#111827')\n"
        "ax.title.set_color('#111827')\n"
        "ax.grid(True, color='#E5E7EB', linewidth=0.8, alpha=0.8)\n"
        "plt.tight_layout()\n"
        "plt.savefig(output_path, dpi=150, facecolor='white', edgecolor='white', transparent=False)\n"
    )
    return header + body + footer
