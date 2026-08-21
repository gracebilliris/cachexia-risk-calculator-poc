"""Synthetic cachexia risk proof-of-concept.

This package is research-only. Its outputs are simulation artifacts and are
not suitable for clinical use.
"""

from .core import calculate_predictors, select_baseline_weight, validate_patient
from .outcomes import evaluate_baseline_status, evaluate_horizon

__all__ = [
    "calculate_predictors",
    "evaluate_baseline_status",
    "evaluate_horizon",
    "select_baseline_weight",
    "validate_patient",
]
