from __future__ import annotations

from backend.app.modules.visualization.schemas import VisualizationResultPayload


def _chart_data() -> dict[str, object]:
    return {
        "chart_type": "bar",
        "x_key": "PassOrFail",
        "y_key": "PassOrFail_count",
        "x": ["0", "1"],
        "series": [{"name": "PassOrFail_count", "y": [2555, 52]}],
        "caption": "양품/불량 분포",
    }


def test_visualization_result_accepts_legacy_chart_aliases() -> None:
    chart = _chart_data()

    result = VisualizationResultPayload.model_validate(
        {
            "status": "generated",
            "source_id": "benchmark-moldset-labeled",
            "summary": "analysis 결과를 바탕으로 bar 시각화를 생성했습니다.",
            "chart": chart,
            "chart_data": chart,
        }
    )

    assert result.chart is not None
    assert result.chart_data is not None
    assert result.chart.chart_type == "bar"
    assert result.chart_data.series[0].name == "PassOrFail_count"


def test_visualization_result_accepts_canonical_charts_list() -> None:
    first = _chart_data()
    second = {
        "chart_type": "bar",
        "x_key": "Reason",
        "y_key": "defect_count",
        "x": ["가스", "미성형"],
        "series": [{"name": "defect_count", "y": [30, 12]}],
        "caption": "불량 사유별 건수",
    }

    result = VisualizationResultPayload.model_validate(
        {
            "status": "generated",
            "source_id": "benchmark-moldset-labeled",
            "summary": "여러 시각화를 생성했습니다.",
            "chart": first,
            "chart_data": first,
            "charts": [first, second],
        }
    )

    assert len(result.charts or []) == 2
    assert result.charts[0].x_key == "PassOrFail"
    assert result.charts[1].x_key == "Reason"


def test_visualization_result_accepts_artifact_and_fallback_table() -> None:
    result = VisualizationResultPayload.model_validate(
        {
            "status": "fallback",
            "source_id": "benchmark-moldset-labeled",
            "summary": "차트 대신 결과 표를 반환합니다.",
            "artifact": {
                "mime_type": "image/png",
                "image_base64": "abc123",
                "code": "print('render')",
            },
            "fallback_table": [{"PassOrFail": "0", "count": 2555}],
        }
    )

    assert result.artifact is not None
    assert result.artifact.mime_type == "image/png"
    assert result.fallback_table == [{"PassOrFail": "0", "count": 2555}]
