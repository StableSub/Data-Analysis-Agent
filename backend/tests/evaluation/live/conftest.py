from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live_benchmark: opt-in benchmark tests that may call external LLM/workflow services")


def live_benchmark_enabled() -> bool:
    return os.environ.get("RUN_LIVE_BENCHMARK") == "1"


def require_live_benchmark() -> None:
    if not live_benchmark_enabled():
        pytest.skip("set RUN_LIVE_BENCHMARK=1 to run opt-in live benchmark tests")
