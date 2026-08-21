"""Transparent, tri-state synthetic outcome engineering."""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from .config import load_simulation_config
from .core import (
    PatientValidationError,
    calculate_predictors,
    parse_date,
    select_baseline_weight,
    validate_patient,
)

_DEFINITIONS = load_simulation_config()["definitions"]
_SARCOPENIA_BRANCH_ENABLED = _DEFINITIONS["fearon_sarcopenia_branch_enabled"]
_SARCOPENIA_STATUS = _DEFINITIONS["sarcopenia_status"]
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


def _latest_follow_up_appetite(
    observations: list[dict[str, Any]],
    prediction_date: date,
    horizon_date: date,
) -> dict[str, Any] | None:
    candidates = []
    for index, observation in enumerate(observations):
        observed = parse_date(observation["date"])
        if prediction_date < observed <= horizon_date:
            candidates.append((observed, index, observation))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _fearon_status(
    loss_percent: float, bmi_at_outcome: float | None, sarcopenia: str
) -> tuple[str, list[str]]:
    reasons = [f"Weight loss for this assessment window is {loss_percent:.3f}%."]
    primary_threshold = _DEFINITIONS["fearon_weight_loss_primary_exclusive"]
    conditional_threshold = _DEFINITIONS[
        "fearon_weight_loss_conditional_exclusive"
    ]
    bmi_threshold = _DEFINITIONS["fearon_bmi_exclusive"]
    if loss_percent > primary_threshold:
        return "yes", reasons + ["Threshold branch met: weight loss >5%."]
    if loss_percent <= conditional_threshold:
        return "no", reasons + ["All conditional branches require weight loss >2%."]
    if bmi_at_outcome is not None and bmi_at_outcome < bmi_threshold:
        return "yes", reasons + ["Threshold branch met: weight loss >2% and BMI <20."]
    if _SARCOPENIA_BRANCH_ENABLED and sarcopenia == "yes":
        return "yes", reasons + [
            "Threshold branch met: weight loss >2% and documented sarcopenia evidence."
        ]
    if bmi_at_outcome is not None and bmi_at_outcome >= bmi_threshold:
        if not _SARCOPENIA_BRANCH_ENABLED:
            return "unknown", reasons + [
                "Not evaluable in v1 because the BMI branch is not met and "
                "the sarcopenia branch is disabled pending a clinical definition."
            ]
        if sarcopenia == "no":
            return "no", reasons + [
                "The BMI and sarcopenia branches are both explicitly refuted."
            ]
    unknown_branches = []
    if bmi_at_outcome is None:
        unknown_branches.append("BMI")
    if _SARCOPENIA_BRANCH_ENABLED and sarcopenia == "unknown":
        unknown_branches.append("sarcopenia")
    if not _SARCOPENIA_BRANCH_ENABLED:
        unknown_branches.append(
            "the sarcopenia branch is disabled pending a clinical definition"
        )
    return "unknown", reasons + [
        "Not evaluable because " + " and ".join(unknown_branches) + "."
    ]


def evaluate_baseline_status(
    patient: dict[str, Any],
    predictors: dict[str, Any] | None = None,
    config: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Evaluate baseline-derived criteria status from retrospective evidence."""

    validate_patient(patient)
    baseline_predictors = predictors or calculate_predictors(patient)
    loss = baseline_predictors["weight_loss_percent"]
    bmi = baseline_predictors["bmi"]
    result = {
        "basis": "baseline_derived_current_status",
        "status": "research_only_criteria_status_not_diagnosis",
        "weight_change_window": "retrospective_observed_up_to_six_months",
        "cachexia_criteria_status": "unknown",
        "precachexia_candidate_status": "unknown",
        "explanations": [
            "Current criteria status is not evaluable without baseline weight change."
        ],
    }
    if loss is None:
        return result
    cachexia, cachexia_reasons = _fearon_status(loss, bmi, patient["sarcopenia"])
    pre_config = {**DEFAULT_PRECACHEXIA_CONFIG, **(config or {})}
    precachexia, pre_reasons = _precachexia_status(
        loss,
        patient["reduced_appetite"],
        cachexia,
        pre_config,
    )
    result.update(
        {
            "cachexia_criteria_status": cachexia,
            "precachexia_candidate_status": precachexia,
            "explanations": cachexia_reasons
            + ["Provisional candidate rule: " + reason for reason in pre_reasons],
        }
    )
    return result


def _outcome_framing(months: int) -> tuple[str, str]:
    if months == 3:
        return (
            _DEFINITIONS["three_month_outcome_status"],
            "The 3-month baseline-to-horizon change looks forward and differs "
            "from Fearon 2011 in both direction and window length.",
        )
    return (
        _DEFINITIONS["six_month_outcome_status"],
        "Although the horizon length is six months, the endpoint looks forward "
        "from baseline and is not a Fearon classification; it is a prospective "
        "research endpoint only, not a diagnosis.",
    )


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
    """Evaluate a qualified research-only threshold outcome."""

    if months not in (3, 6):
        raise PatientValidationError("Only 3- and 6-month horizons are supported.")
    validate_patient(patient)
    prediction_date = parse_date(patient["prediction_date"])
    horizon_date = add_calendar_months(prediction_date, months)
    baseline = select_baseline_weight(patient["weights"], prediction_date)
    outcome_weight = _latest_outcome_weight(
        patient["weights"], prediction_date, horizon_date
    )
    appetite_observation = _latest_follow_up_appetite(
        patient.get("follow_up_appetite_observations", []),
        prediction_date,
        horizon_date,
    )
    appetite = (
        appetite_observation["reduced_appetite"]
        if appetite_observation is not None
        else "unknown"
    )
    status, fearon_comparison = _outcome_framing(months)
    outcome_basis = (
        "observed_synthetic_follow_up"
        if baseline is not None and outcome_weight is not None
        else "insufficient_synthetic_follow_up_evidence"
    )
    result = {
        "horizon_months": months,
        "horizon_date": horizon_date.isoformat(),
        "boundary": "inclusive",
        "outcome_type": "research_only_threshold_based_outcome",
        "outcome_basis": outcome_basis,
        "status": status,
        "fearon_classification": False,
        "fearon_2011_comparison": fearon_comparison,
        "baseline_weight_date": baseline["date"] if baseline else None,
        "outcome_weight_date": outcome_weight["date"] if outcome_weight else None,
        "outcome_interval_days": (
            (
                parse_date(outcome_weight["date"])
                - parse_date(baseline["date"])
            ).days
            if baseline is not None and outcome_weight is not None
            else None
        ),
        "outcome_weight_kg": outcome_weight["weight_kg"] if outcome_weight else None,
        "follow_up_appetite_date": (
            appetite_observation["date"] if appetite_observation else None
        ),
        "follow_up_reduced_appetite": appetite,
        "weight_loss_percent": None,
        "bmi_at_outcome": None,
        "threshold_based_cachexia_status": "unknown",
        "precachexia_candidate_status": "unknown",
        "provenance": {
            "basis": outcome_basis,
            "weight_evidence": (
                "dated_synthetic_follow_up_observation"
                if outcome_weight
                else "unavailable"
            ),
            "appetite_evidence": (
                "dated_synthetic_follow_up_observation"
                if appetite_observation
                else "unavailable_no_baseline_carry_forward"
            ),
            "sarcopenia_evidence": _SARCOPENIA_STATUS,
        },
        "explanations": [
            fearon_comparison,
            "Outcome is not evaluable without baseline and in-horizon weight.",
        ],
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
    cachexia, cachexia_reasons = _fearon_status(loss, bmi, "unknown")
    pre_config = {**DEFAULT_PRECACHEXIA_CONFIG, **(config or {})}
    precachexia, pre_reasons = _precachexia_status(loss, appetite, cachexia, pre_config)
    result.update(
        {
            "weight_loss_percent": loss,
            "bmi_at_outcome": bmi,
            "threshold_based_cachexia_status": cachexia,
            "precachexia_candidate_status": precachexia,
            "explanations": [fearon_comparison]
            + cachexia_reasons
            + ["Provisional candidate rule: " + reason for reason in pre_reasons],
        }
    )
    return result
