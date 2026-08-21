"""Validated baseline predictor construction with strict temporal isolation."""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any, Iterable

from .config import load_simulation_config

_CONFIG = load_simulation_config()
_COHORT = _CONFIG["cohort"]
_DEFINITIONS = _CONFIG["definitions"]
ALLOWED_SEX = {"female", "male", "unknown"}
ALLOWED_STAGE = {"I", "II", "III", "IV", "unknown"}
ALLOWED_TRI_STATE = {"yes", "no", "unknown"}
ALLOWED_ECOG = {0, 1, 2, 3, 4, None}
ALLOWED_CANCER_TYPE = set(_COHORT["cancer_type_probabilities"])
ALLOWED_LUNG_SUBTYPE = {"SCLC", "NSCLC", "unknown"}
MONTH_DAYS = float(_DEFINITIONS["days_per_month"])


class PatientValidationError(ValueError):
    """Raised when a patient contains invalid or implausible values."""


def parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise PatientValidationError("Dates must be ISO YYYY-MM-DD strings.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PatientValidationError(f"Invalid ISO date: {value!r}.") from exc


def _shift_months(value: date, months: int) -> date:
    absolute = value.year * 12 + value.month - 1 + months
    year, month_index = divmod(absolute, 12)
    month = month_index + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _normalise_weights(weights: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalised: list[dict[str, Any]] = []
    for index, measurement in enumerate(weights):
        if not isinstance(measurement, dict):
            raise PatientValidationError("Each weight measurement must be an object.")
        if "date" not in measurement or "weight_kg" not in measurement:
            raise PatientValidationError("Each weight requires date and weight_kg.")
        measured = parse_date(measurement["date"])
        weight = measurement["weight_kg"]
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise PatientValidationError("weight_kg must be numeric.")
        weight_bounds = _COHORT["historical_weight_kg"]
        if not weight_bounds["minimum"] <= float(weight) <= weight_bounds["maximum"]:
            raise PatientValidationError(
                f"weight_kg {weight} is outside the POC permitted range "
                f"{weight_bounds['minimum']}-{weight_bounds['maximum']} kg."
            )
        normalised.append(
            {
                **measurement,
                "date": measured.isoformat(),
                "weight_kg": float(weight),
                "_date": measured,
                "_index": index,
            }
        )
    return normalised


def validate_patient(patient: dict[str, Any]) -> None:
    """Validate required fields; never coerce invalid values or unknowns."""

    required = {
        "patient_id",
        "prediction_date",
        "age",
        "sex",
        "cancer_type",
        "cancer_subtype",
        "cancer_stage",
        "height_cm",
        "weights",
        "ecog",
        "reduced_appetite",
        "sarcopenia",
    }
    missing = sorted(required - patient.keys())
    if missing:
        raise PatientValidationError(f"Missing required fields: {', '.join(missing)}.")
    if not isinstance(patient["patient_id"], str) or not patient["patient_id"].strip():
        raise PatientValidationError("patient_id must be a non-empty synthetic identifier.")
    parse_date(patient["prediction_date"])
    age = patient["age"]
    age_bounds = _COHORT["age"]
    if (
        isinstance(age, bool)
        or not isinstance(age, int)
        or not age_bounds["minimum"] <= age <= age_bounds["maximum"]
    ):
        raise PatientValidationError(
            f"age must be an integer from {age_bounds['minimum']} through "
            f"{age_bounds['maximum']}."
        )
    if patient["sex"] not in ALLOWED_SEX:
        raise PatientValidationError(f"sex must be one of {sorted(ALLOWED_SEX)}.")
    if patient["cancer_type"] not in ALLOWED_CANCER_TYPE:
        raise PatientValidationError(
            f"cancer_type must be one of {sorted(ALLOWED_CANCER_TYPE)}."
        )
    if patient["cancer_type"] == "lung":
        if patient["cancer_subtype"] not in ALLOWED_LUNG_SUBTYPE:
            raise PatientValidationError(
                "Lung cancer_subtype must be SCLC, NSCLC, or unknown."
            )
    elif patient["cancer_subtype"] != "not applicable":
        raise PatientValidationError(
            "Non-lung cancer_subtype must be exactly 'not applicable'."
        )
    if patient["cancer_stage"] not in ALLOWED_STAGE:
        raise PatientValidationError(f"cancer_stage must be one of {sorted(ALLOWED_STAGE)}.")
    height = patient["height_cm"]
    if height is not None:
        if isinstance(height, bool) or not isinstance(height, (int, float)):
            raise PatientValidationError("height_cm must be numeric or null.")
        height_minimum = min(
            values["minimum"] for values in _COHORT["height_cm"].values()
        )
        height_maximum = max(
            values["maximum"] for values in _COHORT["height_cm"].values()
        )
        if not height_minimum <= float(height) <= height_maximum:
            raise PatientValidationError(
                "height_cm is outside the POC permitted range "
                f"{height_minimum}-{height_maximum} cm."
            )
    if patient["ecog"] not in ALLOWED_ECOG:
        raise PatientValidationError("ecog must be 0, 1, 2, 3, 4, or null (unknown).")
    for name in ("reduced_appetite", "sarcopenia"):
        if patient[name] not in ALLOWED_TRI_STATE:
            raise PatientValidationError(f"{name} must be yes, no, or unknown.")
    follow_up_appetite = patient.get("follow_up_appetite_observations", [])
    if not isinstance(follow_up_appetite, list):
        raise PatientValidationError(
            "follow_up_appetite_observations must be a list when provided."
        )
    for observation in follow_up_appetite:
        if not isinstance(observation, dict):
            raise PatientValidationError(
                "Each follow-up appetite observation must be an object."
            )
        if (
            "date" not in observation
            or "reduced_appetite" not in observation
            or "source" not in observation
        ):
            raise PatientValidationError(
                "Each follow-up appetite observation requires date, "
                "reduced_appetite, and source."
            )
        parse_date(observation["date"])
        if observation["reduced_appetite"] not in ALLOWED_TRI_STATE:
            raise PatientValidationError(
                "Follow-up reduced_appetite must be yes, no, or unknown."
            )
        if observation["source"] != "synthetic_follow_up_observation":
            raise PatientValidationError(
                "Follow-up appetite source must be exactly "
                "'synthetic_follow_up_observation'."
            )
    if not isinstance(patient["weights"], list):
        raise PatientValidationError("weights must be a list.")
    _normalise_weights(patient["weights"])


def select_baseline_weight(
    weights: Iterable[dict[str, Any]], prediction_date: str | date
) -> dict[str, Any] | None:
    """Return the latest measurement on/before prediction date.

    If duplicate timestamps exist, the last record in input order wins.
    """

    cutoff = parse_date(prediction_date)
    eligible = [w for w in _normalise_weights(weights) if w["_date"] <= cutoff]
    if not eligible:
        return None
    selected = max(eligible, key=lambda item: (item["_date"], item["_index"]))
    return {key: value for key, value in selected.items() if not key.startswith("_")}


def _select_prior_weight(
    weights: Iterable[dict[str, Any]], baseline: dict[str, Any]
) -> dict[str, Any] | None:
    baseline_date = parse_date(baseline["date"])
    lower_bound = _shift_months(baseline_date, -6)
    candidates = [
        w
        for w in _normalise_weights(weights)
        if lower_bound <= w["_date"] < baseline_date
    ]
    if not candidates:
        return None
    # The oldest eligible record provides the longest observable look-back.
    selected = min(candidates, key=lambda item: (item["_date"], -item["_index"]))
    return {key: value for key, value in selected.items() if not key.startswith("_")}


def calculate_predictors(
    patient: dict[str, Any], trajectory_epsilon_percent: float | None = None
) -> dict[str, Any]:
    """Calculate baseline-only predictors, returning None when not calculable."""

    validate_patient(patient)
    if trajectory_epsilon_percent is None:
        trajectory_epsilon_percent = float(
            _DEFINITIONS["trajectory_epsilon_percent"]
        )
    baseline = select_baseline_weight(patient["weights"], patient["prediction_date"])
    result: dict[str, Any] = {
        "baseline_weight_date": None,
        "baseline_weight_kg": None,
        "prior_weight_date": None,
        "prior_weight_kg": None,
        "bmi": None,
        "weight_loss_percent": None,
        "interval_days": None,
        "weight_loss_kg_per_month": None,
        "weight_loss_percentage_points_per_month": None,
        "trajectory": "unknown",
    }
    if baseline is None:
        return result
    result["baseline_weight_date"] = baseline["date"]
    result["baseline_weight_kg"] = baseline["weight_kg"]
    height = patient["height_cm"]
    if height is not None:
        result["bmi"] = baseline["weight_kg"] / ((float(height) / 100.0) ** 2)
    prior = _select_prior_weight(patient["weights"], baseline)
    if prior is None:
        return result
    interval_days = (parse_date(baseline["date"]) - parse_date(prior["date"])).days
    if interval_days <= 0:
        return result
    loss_kg = prior["weight_kg"] - baseline["weight_kg"]
    loss_percent = loss_kg / prior["weight_kg"] * 100.0
    months = interval_days / MONTH_DAYS
    result.update(
        {
            "prior_weight_date": prior["date"],
            "prior_weight_kg": prior["weight_kg"],
            "weight_loss_percent": loss_percent,
            "interval_days": interval_days,
            "weight_loss_kg_per_month": loss_kg / months,
            "weight_loss_percentage_points_per_month": loss_percent / months,
            "trajectory": (
                "loss"
                if loss_percent > trajectory_epsilon_percent
                else "gain"
                if loss_percent < -trajectory_epsilon_percent
                else "stable"
            ),
        }
    )
    return result
