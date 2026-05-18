from __future__ import annotations

import pytest

from eval_cases import RAW_DIR
from moldset_p0_oracles import (
    REQUIRED_COLUMNS,
    expected_defect_rate_by_part,
    expected_defect_reason_counts,
    expected_label_distribution,
    header,
)
from runtime_assertions import assert_float_close, assert_table_close

pytestmark = pytest.mark.skipif(
    not RAW_DIR.exists(),
    reason="evaluation/raw datasets are local benchmark artifacts",
)


def test_moldset_labeled_schema_has_required_analysis_columns() -> None:
    columns = set(header())

    assert REQUIRED_COLUMNS.issubset(columns)
    assert len(columns) == 47


def test_moldset_labeled_pass_or_fail_distribution_oracle() -> None:
    expected = expected_label_distribution()

    assert expected["total_count"] == 2607
    assert expected["normal_count"] == 2555
    assert expected["defect_count"] == 52
    assert_float_close(expected["defect_rate_pct"], 1.9946298427311087)


def test_moldset_labeled_product_defect_rate_oracle() -> None:
    expected_table = [
        {
            "PART_NAME": "CN7 W/S SIDE MLD'G LH",
            "total_count": 712,
            "defect_count": 9,
            "defect_rate_pct": 1.2640449438202246,
        },
        {
            "PART_NAME": "CN7 W/S SIDE MLD'G RH",
            "total_count": 713,
            "defect_count": 18,
            "defect_rate_pct": 2.524544179523142,
        },
        {
            "PART_NAME": "RG3 MOLD'G W/SHLD, LH",
            "total_count": 591,
            "defect_count": 0,
            "defect_rate_pct": 0.0,
        },
        {
            "PART_NAME": "RG3 MOLD'G W/SHLD, RH",
            "total_count": 591,
            "defect_count": 25,
            "defect_rate_pct": 4.230118443316413,
        },
    ]

    assert_table_close(
        expected_defect_rate_by_part(),
        expected_table,
        key_column="PART_NAME",
        metric_columns=["total_count", "defect_count", "defect_rate_pct"],
    )


def test_moldset_labeled_defect_reason_oracle() -> None:
    assert expected_defect_reason_counts() == [
        {"Reason": "가스", "defect_count": 30},
        {"Reason": "미성형", "defect_count": 12},
        {"Reason": "초기허용불량", "defect_count": 10},
    ]
