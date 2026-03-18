import base64
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ..datasets.reader import DatasetReader
from ..datasets.repository import DataSourceRepository
from .schemas import ManualVizRequest

PYTHON_EXECUTABLE = "/Users/anjeongseob/.virtualenvs/ai_agent/bin/python"
SCRIPT_TIMEOUT_SECONDS = 15


def _serialize_preview_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def _build_preview_rows(
    *,
    df: pd.DataFrame,
    x_key: str,
    y_key: str,
    limit: int = 5,
) -> list[Dict[str, Any]]:
    preview_columns = [column for column in [x_key, y_key] if column]
    if not preview_columns:
        return []
    sample = df[preview_columns].head(limit).copy()
    return [
        {
            str(column): _serialize_preview_value(value)
            for column, value in row.items()
        }
        for row in sample.to_dict(orient="records")
    ]


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
        sample = df[[x_key, y_key]].dropna()
        return not sample.empty
    if chart_type == "box" and y_key:
        if x_key:
            sample = df[[x_key, y_key]].dropna()
            return not sample.empty
        return not df[y_key].dropna().empty
    return False


def _run_chart_script(script_path: Path) -> Dict[str, Any]:
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


class VisualizationService:
    """수동 시각화용 데이터 추출을 담당한다."""

    def __init__(
        self,
        *,
        repository: DataSourceRepository,
        reader: DatasetReader,
    ) -> None:
        self.repository = repository
        self.reader = reader

    def load_sample_frame(self, source_id: str, *, nrows: int) -> pd.DataFrame | None:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset or not dataset.storage_path:
            return None
        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None
        return self.reader.read_csv(dataset.storage_path, nrows=nrows)

    def build_execution_code(
        self,
        *,
        source_id: str,
        chart_type: str,
        x_key: str,
        y_key: str,
        output_filename: str,
        max_points: int,
        x_is_datetime: bool,
    ) -> str | None:
        dataset = self.repository.get_by_source_id(source_id)
        if not dataset or not dataset.storage_path:
            return None
        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return None
        return _build_python_code(
            dataset_path=str(file_path),
            chart_type=chart_type,
            x_key=x_key,
            y_key=y_key,
            output_filename=output_filename,
            max_points=max_points,
            x_is_datetime=x_is_datetime,
        )

    def build_preview_rows(
        self,
        *,
        source_id: str,
        x_key: str,
        y_key: str,
        limit: int = 5,
    ) -> list[Dict[str, Any]]:
        df = self.load_sample_frame(source_id, nrows=limit)
        if df is None or df.empty:
            return []
        return _build_preview_rows(df=df, x_key=x_key, y_key=y_key, limit=limit)

    def execute_generated_chart(
        self,
        *,
        source_id: str,
        chart_type: str,
        x_key: str,
        y_key: str,
        python_code: str,
        output_filename: str,
        x_is_datetime: bool,
        max_sample_rows: int,
    ) -> Dict[str, Any]:
        dataset = self.repository.get_by_source_id(source_id) if source_id else None
        if dataset is None or not dataset.storage_path:
            return {
                "status": "unavailable",
                "source_id": source_id,
                "summary": "시각화 대상 데이터셋을 찾지 못했습니다.",
            }

        file_path = Path(dataset.storage_path)
        if not file_path.exists() or not file_path.is_file():
            return {
                "status": "unavailable",
                "source_id": source_id,
                "summary": "데이터 파일이 없어 차트를 생성하지 못했습니다.",
            }

        df = self.reader.read_csv(dataset.storage_path, nrows=max_sample_rows)
        if df.empty or not _chart_has_data(
            df=df,
            chart_type=chart_type,
            x_key=x_key,
            y_key=y_key,
            x_is_datetime=x_is_datetime,
        ):
            return {
                "status": "unavailable",
                "source_id": source_id,
                "summary": "선택된 컬럼에서 유효한 시각화 데이터가 없습니다.",
            }

        temp_dir = Path(tempfile.mkdtemp(prefix="viz_exec_"))
        script_path = temp_dir / "render_chart.py"
        output_path = temp_dir / output_filename
        script_path.write_text(python_code, encoding="utf-8")

        run_result = _run_chart_script(script_path)
        if bool(run_result.get("timed_out", False)):
            return {
                "status": "unavailable",
                "source_id": source_id,
                "summary": "시각화 코드 실행 시간이 초과되어 차트를 생성하지 못했습니다.",
            }

        if int(run_result.get("returncode", 1)) != 0 or not output_path.exists():
            stderr_text = str(run_result.get("stderr") or "").strip()
            error_message = (
                stderr_text.splitlines()[-1]
                if stderr_text
                else "시각화 코드 실행에 실패했습니다."
            )
            return {
                "status": "unavailable",
                "source_id": source_id,
                "summary": f"시각화 코드 실행 실패: {error_message}",
            }

        image_base64 = base64.b64encode(output_path.read_bytes()).decode("ascii")
        axis_text = f"{x_key} vs {y_key}" if x_key and y_key else (x_key or y_key or "-")
        return {
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

    def get_manual_viz_data(self, request: ManualVizRequest) -> Dict[str, Any]:
        dataset = self.repository.get_by_source_id(request.source_id)
        if not dataset:
            return {"error": "NOT_FOUND", "message": "데이터셋을 찾을 수 없습니다."}

        requested_cols = [request.columns.x, request.columns.y]
        if request.columns.color:
            requested_cols.append(request.columns.color)
        if request.columns.group:
            requested_cols.append(request.columns.group)
        requested_cols = list(dict.fromkeys(requested_cols))

        try:
            df = self.reader.read_csv(
                dataset.storage_path,
                nrows=request.limit,
                usecols=requested_cols,
            )
        except FileNotFoundError:
            return {"error": "FILE_NOT_FOUND", "message": "파일이 존재하지 않습니다."}
        except ValueError as exc:
            return {"error": "INVALID_COLUMN", "message": str(exc)}
        except Exception as exc:
            return {"error": "INTERNAL_ERROR", "message": f"데이터 처리 중 오류: {exc}"}

        if df.empty:
            return {"error": "NO_DATA", "message": "조회된 데이터가 없습니다."}

        return {
            "chart_type": request.chart_type,
            "data": df.where(pd.notnull(df), None).to_dict(orient="records"),
        }
