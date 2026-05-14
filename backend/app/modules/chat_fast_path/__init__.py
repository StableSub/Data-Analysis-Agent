"""Deterministic chat fast path helpers."""

from .dataset_answer import FastDatasetAnswer, try_fast_dataset_answer

__all__ = ["FastDatasetAnswer", "try_fast_dataset_answer"]
