"""Transparent, tri-state synthetic outcome engineering."""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from .config import load_simulation_config
from .core import PatientValidationError, parse_date, select_baseline_weight, validate_patient

_DEFINITIONS = load_simulation_config()["definitions"]
_SARCOPENIA_BRANCH_ENABLED = _DEFINITIONS["fearon_sarcopenia_branch_enabled"]
DEFAULT_PRECACHEXIA_CONFIG = {
    "lower_weight_loss_percent_exclusive": _DEFINITIONS[
        "precachexia_lower_weight_loss_percent_exclusive"
    ],
    "upper_weight_loss_percent_inclusive": _DEFINITIONS[
        "precachexia_upper_weight_loss_percent_inclusive"
    ],
}


def add_calendar_months(value: str | date, months: int) -> date:
    """Add calendar months, clamping to the destination month's last day."""

    source = parse_date(value)
    absolute = source.year * 12 + source.month - 1 + months
    year, month_index = divmod(absolute, 12)
    month = month_index + 1
    day = min(source.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _latest_outcome_weight(
    weights: list[dict[str, Any]], prediction_date: date, horizon_date: date
) -> dict[str, Any] | None:
    candidates = []
    for index, measurement in enumerate(weights):
        measured = parse_date(measurement["date"])
        if prediction_date < measured <= horizon_date:
            candidates.append((measured, index, measurement))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _fearon_status(
    loss_percent: float, bmi_at_outcome: float | None, sarcopenia: str
) -> tuple[str, list[str]]:
    reasons = [f"Observed weight loss is {loss_percent:.3f}%."]
    primary_threshold = _DEFINITIONS["fearon_weight_loss_primary_exclusive"]
    conditional_threshold = _DEFINITIONS[
        "fearon_weight_loss_conditional_exclusive"
    ]
    bmi_threshold = _DEFINITIONS["fearon_bmi_exclusive"]
    if loss_percent > primary_threshold:
        return "yes", reasons + ["Supported branch: weight loss >5%."]
    if loss_percent <= conditional_threshold:
        return "no", reasons + ["All supported branches require weight loss >2%."]
    if bmi_at_outcome is not None and bmi_at_outcome < bmi_threshold:
        return "yes", reasons + ["Supported branch: weight loss >2% and BMI <20."]
    if _SARCOPENIA_BRANCH_ENABLED and sarcopenia == "yes":
        return "yes", reasons + [
            "Supported branch: weight loss >2% and documented sarcopenia evidence."
        ]
    if (
        bmi_at_outcome is not None
        and bmi_at_outcome >= bmi_threshold
        and (not _SARCOPENIA_BRANCH_ENABLED or sarcopenia == "no")
    ):
        return "no", reasons + [
            "The BMI and sarcopenia branches are both explicitly refuted."
        ]
    unknown_branches = []
    if bmi_at_outcome is None:
        unknown_branches.append("BMI")
    if _SARCOPENIA_BRANCH_ENABLED and sarcopenia == "unknown":
        unknown_branches.append("sarcopenia")
    return "unknown", reasons + [
        "Not evaluable because " + " and ".join(unknown_branches) + " are unknown."
    ]


def _precachexia_status(
    loss_percent: float,
    appetite: str,
    cachexia: str,
    config: dict[str, float],
) -> tuple[str, list[str]]:
    if cachexia != "no":
        return (
            "unknown" if cachexia == "unknown" else "no",
            ["Candidate pre-cachexia is evaluated only after cachexia is excluded."],
        )
    lower = config["lower_weight_loss_percent_exclusive"]
    upper = config["upper_weight_loss_percent_inclusive"]
    limited_loss = lower < loss_percent <= upper
    if not limited_loss:
        return "no", [f"Weight loss is outside the candidate interval ({lower}, {upper}]."]
    if appetite == "yes":
        return "yes", ["Limited weight loss and reduced appetite are both present."]
    if appetite == "no":
        return "no", ["Reduced appetite is explicitly absent."]
    return "unknown", ["Reduced appetite is unknown."]


def evaluate_horizon(
    patient: dict[str, Any],
    months: int,
    config: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate a 3- or 6-month outcome using inclusive calendar boundaries."""

    if months not in (3, 6):
        raise PatientValidationError("Only 3- and 6-month horizons are supported.")
    validate_patient(patient)
    prediction_date = parse_date(patient["prediction_date"])
    horizon_date = add_calendar_months(prediction_date, months)
    baseline = select_baseline_weight(patient["weights"], prediction_date)
    outcome_weight = _latest_outcome_weight(
        patient["weights"], prediction_date, horizon_date
    )
    result = {
        "horizon_months": months,
        "horizon_date": horizon_date.isoformat(),
        "boundary": "inclusive",
        "baseline_weight_date": baseline["date"] if baseline else None,
        "outcome_weight_date": outcome_weight["date"] if outcome_weight else None,
        "outcome_weight_kg": outcome_weight["weight_kg"] if outcome_weight else None,
        "weight_loss_percent": None,
        "bmi_at_outcome": None,
        "cachexia": "unknown",
        "precachexia_candidate": "unknown",
        "explanations": ["Outcome is not evaluable without baseline and in-horizon weight."],
    }
    if baseline is None or outcome_weight is None:
        return result
    loss = (
        (float(baseline["weight_kg"]) - float(outcome_weight["weight_kg"]))
        / float(baseline["weight_kg"])
        * 100.0
    )
    height = patient["height_cm"]
    bmi = (
        float(outcome_weight["weight_kg"]) / ((float(height) / 100.0) ** 2)
        if height is not None
        else None
    )
    cachexia, cachexia_reasons = _fearon_status(loss, bmi, patient["sarcopenia"])
    pre_config = {**DEFAULT_PRECACHEXIA_CONFIG, **(config or {})}
    precachexia, pre_reasons = _precachexia_status(
        loss, patient["reduced_appetite"], cachexia, pre_config
    )
    result.update(
        {
            "weight_loss_percent": loss,
            "bmi_at_outcome": bmi,
            "cachexia": cachexia,
            "precachexia_candidate": precachexia,
            "explanations": cachexia_reasons + [
                "Provisional pre-cachexia: " + reason for reason in pre_reasons
            ],
        }
    )
    return result
