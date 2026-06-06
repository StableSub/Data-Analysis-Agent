from __future__ import annotations

from backend.app.modules.chat_fast_path.decision import decide_common_analytics_fast_path
from backend.app.modules.profiling.schemas import DatasetContext


class _DefectReasonDatasetContextService:
    def build_context(self, source_id: str) -> DatasetContext:
        return DatasetContext(
            source_id=source_id,
            filename="moldset_labeled.csv",
            available=True,
            row_count_total=7,
            row_count_sample=3,
            column_count=2,
            columns=["PassOrFail", "Reason"],
            dtypes={"PassOrFail": "int64", "Reason": "object"},
            categorical_columns=["PassOrFail", "Reason"],
            group_key_columns=["PassOrFail", "Reason"],
            sample_rows=[
                {"PassOrFail": 0, "Reason": None},
                {"PassOrFail": 1, "Reason": "가스"},
                {"PassOrFail": 1, "Reason": "미성형"},
            ],
        )


def test_explicit_defect_reason_count_question_is_not_fast_path() -> None:
    dataset_context = _DefectReasonDatasetContextService().build_context("dataset-source")

    decision = decide_common_analytics_fast_path(
        question="PassOrFail 값이 1인 데이터의 불량 사유별 건수를 알려줘.",
        dataset_context=dataset_context.model_dump(),
    )

    assert decision.eligible is False
    assert not hasattr(decision, "filters")
    assert decision.blockers


def test_defect_reason_count_fast_path_result_has_no_filter_contract() -> None:
    dataset_context = _DefectReasonDatasetContextService().build_context("dataset-source")

    decision = decide_common_analytics_fast_path(
        question="PassOrFail=1인 불량 데이터만 대상으로 불량 사유별 건수를 알려줘.",
        dataset_context=dataset_context.model_dump(),
    )
    payload = decision.to_fast_path_result()

    assert decision.eligible is False
    assert "filters" not in payload


def test_pass_or_fail_value_grouping_does_not_hard_code_defect_filter() -> None:
    dataset_context = _DefectReasonDatasetContextService().build_context("dataset-source")

    decision = decide_common_analytics_fast_path(
        question="PassOrFail 값별 불량 사유별 건수를 알려줘.",
        dataset_context=dataset_context.model_dump(),
    )

    assert decision.eligible is False
    assert not hasattr(decision, "filters")
