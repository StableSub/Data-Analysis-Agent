from __future__ import annotations

from collections.abc import Mapping

from backend.app.modules.chat_fast_path import try_fast_dataset_answer


def _rich_dataset_context() -> Mapping[str, object]:
    filler_columns = [f"Sensor_{index:02d}" for index in range(1, 49)]
    columns = [
        "TimeStamp",
        "PART_NO",
        "PART_NAME",
        "EQUIP_NAME",
        "Mold_Temperature",
        "Injection_Pressure",
        "PassOrFail",
        "Reason",
        "Shift",
        *filler_columns,
    ]
    return {
        "source_id": "dataset-source",
        "filename": "moldset_labeled.csv",
        "available": True,
        "row_count_total": 2607,
        "row_count_sample": 3,
        "column_count": 57,
        "columns": columns,
        "dtypes": {
            "TimeStamp": "datetime64[ns]",
            "PART_NO": "object",
            "PART_NAME": "object",
            "EQUIP_NAME": "object",
            "Mold_Temperature": "float64",
            "Injection_Pressure": "float64",
            "PassOrFail": "int64",
            "Reason": "object",
            "Shift": "object",
        },
        "datetime_columns": ["TimeStamp"],
        "group_key_columns": ["PART_NO", "PART_NAME", "EQUIP_NAME"],
        "numeric_columns": ["Mold_Temperature", "Injection_Pressure", "PassOrFail"],
        "categorical_columns": ["Reason", "Shift"],
        "identifier_columns": ["PART_NO"],
        "type_columns": {
            "datetime": ["TimeStamp"],
            "group_key": ["PART_NO", "PART_NAME", "EQUIP_NAME"],
            "numerical": ["Mold_Temperature", "Injection_Pressure", "PassOrFail"],
            "categorical": ["Reason", "Shift"],
            "identifier": ["PART_NO"],
        },
        "column_value_samples": {
            "TimeStamp": ["2026-05-01 00:00:00"],
            "PART_NAME": ["Bracket-A"],
            "Mold_Temperature": [211.4],
            "Reason": ["미성형"],
        },
        "quality_summary": {
            "missing_total": 32,
            "missing_ratio": 0.000216,
            "top_missing_columns": [
                {"column": "Reason", "missing_count": 32, "missing_rate": 0.0123}
            ],
        },
    }


def _answer_for(
    question: str,
    dataset_context: Mapping[str, object] | None = None,
) -> str:
    result = _fast_answer_for(question, dataset_context)
    assert result is not None
    content = result.output["content"]
    assert isinstance(content, str)
    return content


def _fast_answer_for(
    question: str,
    dataset_context: Mapping[str, object] | None = None,
):
    return try_fast_dataset_answer(
        question,
        dataset_context or _rich_dataset_context(),
    )


def test_shape_question_with_major_columns_requires_llm_path() -> None:
    result = _fast_answer_for("이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.")

    assert result is None


def test_plain_row_count_question_includes_adjacent_metadata_context() -> None:
    content = _answer_for("이 데이터셋은 몇 행이야?")

    assert "2,607행" in content
    assert "57열" in content
    assert "주요 컬럼" in content
    assert "컬럼 구성" in content


def test_plain_column_count_question_includes_adjacent_metadata_context() -> None:
    content = _answer_for("컬럼 수는 몇 개야?")

    assert "57열" in content
    assert "2,607행" in content
    assert "주요 컬럼" in content
    assert "컬럼 구성" in content


def test_dataset_summary_question_requires_llm_path() -> None:
    result = _fast_answer_for("데이터셋 요약해줘.")

    assert result is None


def test_column_meaning_summary_question_skips_dataset_lookup_fast_path() -> None:
    result = try_fast_dataset_answer(
        "각 컬럼이 무엇을 의미하는지 요약해줘.",
        _rich_dataset_context(),
    )

    assert result is None


def test_all_columns_request_requires_llm_path() -> None:
    result = _fast_answer_for("전체 컬럼을 모두 설명해줘.")

    assert result is None


def test_column_list_and_type_request_requires_llm_path() -> None:
    result = _fast_answer_for("컬럼 목록과 타입을 정리해줘.")

    assert result is None


def test_uppercase_category_question_lists_categorical_columns() -> None:
    content = _answer_for("CATEGORY columns 알려줘.")

    assert "총 2개 범주형 컬럼입니다." in content
    assert "Reason (object)" in content
    assert "Shift (object)" in content
    assert "Mold_Temperature" not in content


def test_shape_question_without_columns_still_requires_llm_path() -> None:
    empty_columns: list[str] = []
    context: dict[str, object] = {
        "available": True,
        "row_count_total": 12,
        "column_count": 0,
        "columns": empty_columns,
    }

    result = _fast_answer_for("이 데이터셋의 행 수, 컬럼 수, 주요 컬럼을 요약해줘.", context)

    assert result is None


def test_complex_analytic_question_still_skips_dataset_lookup_fast_path() -> None:
    result = try_fast_dataset_answer(
        "PassOrFail 값이 1인 데이터의 불량 사유별 건수를 알려줘.",
        _rich_dataset_context(),
    )

    assert result is None
