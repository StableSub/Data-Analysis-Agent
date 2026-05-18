from __future__ import annotations

import os

import pytest

from eval_cases import load_all_cases
from runtime_assertions import route_accuracy

pytestmark = pytest.mark.live_benchmark


def _require_live_benchmark() -> None:
    if os.environ.get("RUN_LIVE_BENCHMARK") != "1":
        pytest.skip("set RUN_LIVE_BENCHMARK=1 to run opt-in live benchmark tests")


def test_live_benchmark_is_opt_in_and_has_case_manifest() -> None:
    _require_live_benchmark()
    if "OPENAI_API_KEY" not in os.environ:
        pytest.skip("OPENAI_API_KEY is required for live LLM workflow benchmark runs")

    cases = load_all_cases()
    assert len(cases) >= 8
    assert route_accuracy([{**case, "actual_route": case["expected_route"]} for case in cases]) == 1.0


def test_live_benchmark_requires_uploaded_dataset_sources() -> None:
    _require_live_benchmark()
    if "BENCHMARK_SOURCE_ID_MOLDSET_LABELED" not in os.environ:
        pytest.skip("set BENCHMARK_SOURCE_ID_MOLDSET_LABELED after uploading benchmark datasets to run full workflow")

    assert os.environ["BENCHMARK_SOURCE_ID_MOLDSET_LABELED"].strip()
