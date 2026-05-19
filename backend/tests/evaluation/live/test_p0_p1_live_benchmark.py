from __future__ import annotations

import pytest

from conftest import require_benchmark_dataset, require_live_benchmark, selected_live_case_ids
from eval_cases import load_all_cases
from runtime_assertions import route_accuracy

pytestmark = pytest.mark.live_benchmark


def test_live_benchmark_is_opt_in_and_has_case_manifest() -> None:
    require_live_benchmark()

    cases = load_all_cases()
    assert len(cases) >= 8
    assert route_accuracy([{**case, "actual_route": case["expected_route"]} for case in cases]) == 1.0


def test_live_benchmark_auto_loads_selected_raw_datasets() -> None:
    require_live_benchmark()
    selected_ids = set(selected_live_case_ids())
    selected_cases = [case for case in load_all_cases() if case["case_id"] in selected_ids]

    assert selected_cases, {"selected_case_ids": sorted(selected_ids)}
    for case in selected_cases:
        registration = require_benchmark_dataset(case["dataset"])
        assert registration.storage_path.exists(), {
            "case_id": case["case_id"],
            "dataset": case["dataset"],
            "storage_path": str(registration.storage_path),
        }
        assert registration.source_id.startswith("benchmark-") or registration.source_id.strip()
