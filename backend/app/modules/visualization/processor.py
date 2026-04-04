from __future__ import annotations

from datetime import datetime
from typing import Any

from ..analysis.schemas import (
    AnalysisExecutionResult,
    AnalysisPlan,
    ChartData,
    ChartSeries,
    VisualizationOutput,
)


# analysis 결과 기반 자동 시각화 후처리를 담당한다.
class VisualizationProcessor:
    """Build chart-friendly output from analysis results."""

    # analysis 결과와 시각화 힌트를 받아 chart_data 또는 fallback_table을 생성한다.
    def build_from_analysis_result(
        self,
        *,
        analysis_plan: AnalysisPlan,
        analysis_result: AnalysisExecutionResult,
    ) -> VisualizationOutput:
        if analysis_result.execution_status != "success":
            return VisualizationOutput(status="unavailable")

        # 자동 시각화의 기본 입력은 analysis 결과 table이다.
        table = list(analysis_result.table or [])
        if not table:
            return VisualizationOutput(status="unavailable")

        # table 구조와 visualization_hint를 바탕으로 차트 스펙을 결정한다.
        chart_spec = self._resolve_chart_spec(
            table=table,
            analysis_plan=analysis_plan,
        )
        if chart_spec is None:
            return VisualizationOutput(
                status="fallback",
                fallback_table=table,
            )

        chart_type, x_key, y_key, series_key, caption = chart_spec
        # 선택된 차트 스펙을 프론트용 chart_data 구조로 변환한다.
        chart_data = self._build_chart_data(
            table=table,
            chart_type=chart_type,
            x_key=x_key,
            y_key=y_key,
            series_key=series_key,
            caption=caption,
        )
        if chart_data is None:
            return VisualizationOutput(
                status="fallback",
                fallback_table=table,
            )

        return VisualizationOutput(
            status="generated",
            chart_data=chart_data,
            fallback_table=None,
        )

    # 결과 표 컬럼 구조를 보고 chart_type, x/y 축, series 기준을 결정한다.
    def _resolve_chart_spec(
        self,
        *,
        table: list[dict[str, Any]],
        analysis_plan: AnalysisPlan,
    ) -> tuple[str, str, str, str | None, str | None] | None:
        first_row = table[0] if table else {}
        columns = list(first_row.keys())
        if not columns:
            return None

        numeric_columns = [
            column for column in columns if self._is_numeric_column(table, column)
        ]
        datetime_columns = [
            column for column in columns if self._is_datetime_column(table, column)
        ]
        time_axis_columns = [
            column
            for column in columns
            if column in {"hour", "date", "week", "month", "quarter", "year"}
        ]
        categorical_columns = [
            column
            for column in columns
            if column not in numeric_columns and column not in datetime_columns
        ]

        hint = analysis_plan.visualization_hint
        preferred_chart = (
            hint.preferred_chart if hint.preferred_chart != "none" else None
        )
        x_key = hint.x if hint.x in columns else None
        y_key = hint.y if hint.y in columns else None
        series_key = hint.series if hint.series in columns else None
        caption = hint.caption or analysis_result_caption(analysis_plan)

        # line 힌트가 있으면 시간축 + 수치값 조합을 먼저 시도한다.
        if preferred_chart == "line":
            resolved_x = x_key or (
                datetime_columns[0]
                if datetime_columns
                else (time_axis_columns[0] if time_axis_columns else None)
            )
            resolved_y = y_key or (numeric_columns[0] if numeric_columns else None)
            if (
                resolved_x
                and resolved_y
                and (resolved_x in datetime_columns or resolved_x in time_axis_columns)
            ):
                resolved_series = series_key or self._pick_series_key(
                    categorical_columns=categorical_columns,
                    excluded={resolved_x, resolved_y},
                )
                return ("line", resolved_x, resolved_y, resolved_series, caption)

        # bar 힌트가 있으면 범주축 + 수치값 조합을 우선 시도한다.
        if preferred_chart == "bar":
            resolved_x = x_key or self._pick_bar_x(
                categorical_columns, datetime_columns
            )
            resolved_y = y_key or (numeric_columns[0] if numeric_columns else None)
            if resolved_x and resolved_y:
                resolved_series = series_key or self._pick_series_key(
                    categorical_columns=categorical_columns,
                    excluded={resolved_x, resolved_y},
                )
                return ("bar", resolved_x, resolved_y, resolved_series, caption)

        # scatter 힌트가 있으면 수치형 2축 조합을 우선 시도한다.
        if preferred_chart == "scatter":
            resolved_x = x_key or (
                numeric_columns[0] if len(numeric_columns) >= 1 else None
            )
            resolved_y = y_key or (
                numeric_columns[1] if len(numeric_columns) >= 2 else None
            )
            if resolved_x and resolved_y:
                return ("scatter", resolved_x, resolved_y, None, caption)

        # 힌트가 없어도 시간축 + 수치값이면 line 차트를 기본 선택한다.
        if (datetime_columns or time_axis_columns) and numeric_columns:
            resolved_x = x_key or (
                datetime_columns[0] if datetime_columns else time_axis_columns[0]
            )
            resolved_y = y_key or numeric_columns[0]
            resolved_series = series_key or self._pick_series_key(
                categorical_columns=categorical_columns,
                excluded={resolved_x, resolved_y},
            )
            return ("line", resolved_x, resolved_y, resolved_series, caption)

        # 범주형 + 수치형 조합이면 bar 차트를 기본 선택한다.
        if categorical_columns and numeric_columns:
            resolved_x = x_key or categorical_columns[0]
            resolved_y = y_key or numeric_columns[0]
            resolved_series = series_key or self._pick_series_key(
                categorical_columns=categorical_columns,
                excluded={resolved_x, resolved_y},
            )
            return ("bar", resolved_x, resolved_y, resolved_series, caption)

        # 수치형 컬럼이 2개 이상이면 scatter 후보로 본다.
        if len(numeric_columns) >= 2:
            return (
                "scatter",
                x_key or numeric_columns[0],
                y_key or numeric_columns[1],
                None,
                caption,
            )

        return None

    def _build_chart_data(
        self,
        *,
        table: list[dict[str, Any]],
        chart_type: str,
        x_key: str,
        y_key: str,
        series_key: str | None,
        caption: str | None,
    ) -> ChartData | None:
        if chart_type in {"line", "bar"}:
            if series_key:
                x_values = self._unique_preserve_order(row.get(x_key) for row in table)
                series_names = self._unique_preserve_order(
                    row.get(series_key) for row in table
                )
                if not x_values or not series_names:
                    return None

                lookup = {
                    (row.get(series_key), row.get(x_key)): row.get(y_key)
                    for row in table
                }
                series = [
                    ChartSeries(
                        name=str(series_name),
                        y=[lookup.get((series_name, x_value)) for x_value in x_values],
                    )
                    for series_name in series_names
                    if series_name is not None
                ]
                if not series:
                    return None
                return ChartData(
                    chart_type=chart_type,
                    x=list(x_values),
                    series=series,
                    caption=caption,
                )

            x_values = [row.get(x_key) for row in table]
            y_values = [row.get(y_key) for row in table]
            if not x_values or not y_values:
                return None
            return ChartData(
                chart_type=chart_type,
                x=x_values,
                series=[ChartSeries(name=y_key, y=y_values)],
                caption=caption,
            )

        if chart_type == "scatter":
            x_values = [row.get(x_key) for row in table]
            y_values = [row.get(y_key) for row in table]
            if not x_values or not y_values:
                return None
            return ChartData(
                chart_type="scatter",
                x=x_values,
                series=[ChartSeries(name=y_key, y=y_values)],
                caption=caption,
            )

        return None

    # x/y 축에 쓰지 않은 범주형 컬럼 중 첫 번째를 series 후보로 선택한다.
    def _pick_series_key(
        self,
        *,
        categorical_columns: list[str],
        excluded: set[str],
    ) -> str | None:
        for column in categorical_columns:
            if column not in excluded:
                return column
        return None

    # bar 차트의 x축은 범주형을 우선 사용하고 없으면 datetime 컬럼을 사용한다.
    def _pick_bar_x(
        self,
        categorical_columns: list[str],
        datetime_columns: list[str],
    ) -> str | None:
        if categorical_columns:
            return categorical_columns[0]
        if datetime_columns:
            return datetime_columns[0]
        return None

    # 컬럼 값 다수가 숫자면 수치형 컬럼으로 본다.
    def _is_numeric_column(self, table: list[dict[str, Any]], column: str) -> bool:
        values = [row.get(column) for row in table if row.get(column) is not None]
        if not values:
            return False
        numeric_count = sum(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in values
        )
        return numeric_count / len(values) >= 0.7

    # 컬럼 값 다수가 datetime으로 파싱되면 시간축 컬럼으로 본다.
    def _is_datetime_column(self, table: list[dict[str, Any]], column: str) -> bool:
        values = [row.get(column) for row in table if row.get(column) is not None]
        if not values:
            return False
        parsed_count = 0
        for value in values:
            if isinstance(value, datetime):
                parsed_count += 1
                continue
            if not isinstance(value, str):
                continue
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                parsed_count += 1
            except ValueError:
                continue
        return parsed_count / len(values) >= 0.7

    # 중복을 제거하되 원래 등장 순서는 유지된다.
    def _unique_preserve_order(self, values: Any) -> list[Any]:
        ordered: list[Any] = []
        seen: list[Any] = []
        for value in values:
            if value is None:
                continue
            if value in seen:
                continue
            seen.append(value)
            ordered.append(value)
        return ordered


# visualization_hint caption이 있으면 사용하고 없으면 analysis objective를 제목으로 사용한다.
def analysis_result_caption(analysis_plan: AnalysisPlan) -> str:
    hint_caption = analysis_plan.visualization_hint.caption
    if isinstance(hint_caption, str) and hint_caption.strip():
        return hint_caption.strip()
    return analysis_plan.objective.strip() or analysis_plan.analysis_type
