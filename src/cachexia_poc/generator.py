"""Explainable, reproducible synthetic longitudinal cohort generation."""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from .config import DEFAULT_CONFIG_PATH, load_simulation_config
from .core import calculate_predictors
from .outcomes import add_calendar_months, evaluate_horizon

def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Backward-compatible public alias for the centralized config loader."""

    return load_simulation_config(config_path or DEFAULT_CONFIG_PATH)


def _weighted_choice(rng: random.Random, probabilities: dict[str, float]) -> str:
    values = list(probabilities)
    weights = [float(probabilities[value]) for value in values]
    if any(weight < 0 for weight in weights) or not math.isclose(
        sum(weights), 1.0, abs_tol=1e-8
    ):
        raise ValueError("Configured probabilities must be non-negative and sum to 1.")
    return rng.choices(values, weights=weights, k=1)[0]


def _bounded_gaussian(
    rng: random.Random, mean: float, sd: float, minimum: float, maximum: float
) -> float:
    for _ in range(100):
        value = rng.gauss(mean, sd)
        if minimum <= value <= maximum:
            return value
    raise RuntimeError("Unable to draw a bounded synthetic value after 100 attempts.")


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _risk_output(
    patient: dict[str, Any],
    predictors: dict[str, Any],
    horizon_key: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    assumptions = config["risk_outputs"][horizon_key]
    if (
        config["definitions"]["risk_missing_predictor_policy"] == "withhold"
        and (
            predictors["weight_loss_percent"] is None
            or predictors["bmi"] is None
        )
    ):
        return {
            "probability": None,
            "band": "unknown",
            "score": None,
            "explanation": [
                "Estimate withheld: BMI and baseline weight change are required."
            ],
            "warning": "Simulation assumption; not clinically validated.",
        }
    score = float(assumptions["intercept"])
    factors: list[str] = []
    if patient["age"] > config["risk_outputs"]["age_threshold_exclusive"]:
        score += assumptions["age_over_55"]
        factors.append("age >55 simulation term")
    stage_term = assumptions["stage"][patient["cancer_stage"]]
    score += stage_term
    if stage_term:
        factors.append(f"stage {patient['cancer_stage']} simulation term")
    ecog_key = "unknown" if patient["ecog"] is None else str(patient["ecog"])
    ecog_term = assumptions["ecog"][ecog_key]
    score += ecog_term
    if ecog_term:
        factors.append(f"ECOG {ecog_key} simulation term")
    appetite_term = assumptions["appetite"][patient["reduced_appetite"]]
    score += appetite_term
    if appetite_term:
        factors.append(f"appetite={patient['reduced_appetite']} simulation term")
    loss = predictors["weight_loss_percent"]
    if loss is not None and loss > 0:
        score += loss * assumptions["baseline_weight_loss_per_percent"]
        factors.append(f"baseline weight loss {loss:.1f}% simulation term")
    bmi = predictors["bmi"]
    if bmi is not None and bmi < 20:
        score += assumptions["low_bmi_under_20"]
        factors.append("BMI <20 simulation term")
    cancer_points = config["simulation_relationships"]["cancer_latent_points"][
        patient["cancer_type"]
    ]
    cancer_term = cancer_points * assumptions["cancer_type_multiplier"]
    score += cancer_term
    if cancer_term:
        factors.append(f"{patient['cancer_type']} simulation term")
    probability = _sigmoid(score)
    bands = config["risk_outputs"]["band_thresholds"]
    band = (
        "low"
        if probability < bands["low_upper_exclusive"]
        else "high"
        if probability >= bands["high_lower_inclusive"]
        else "medium"
    )
    return {
        "probability": probability,
        "band": band,
        "score": score,
        "explanation": factors or ["intercept-only simulation estimate"],
        "warning": "Simulation assumption; not clinically validated.",
    }


def _edge_case_override(
    index: int,
    patient: dict[str, Any],
    baseline_weight: float,
    prediction_date: date,
    assumptions: dict[str, float],
) -> tuple[list[dict[str, Any]], str | None]:
    """Create deterministic, labelled examples for reviewer boundary inspection."""

    if index == 0:
        patient["ecog"] = None
        patient["reduced_appetite"] = "unknown"
        return [{"date": prediction_date.isoformat(), "weight_kg": baseline_weight}], "unknown_fields"
    if index == 1:
        return [{"date": prediction_date.isoformat(), "weight_kg": baseline_weight}], "insufficient_history"
    if index == 2:
        gain = assumptions["baseline_weight_gain_percent"] / 100.0
        weights = [
            {"date": add_calendar_months(prediction_date, -6).isoformat(), "weight_kg": baseline_weight * (1.0 - gain)},
            {"date": prediction_date.isoformat(), "weight_kg": baseline_weight},
        ]
        return weights, "baseline_weight_gain"
    if index == 3:
        weights = [
            {"date": add_calendar_months(prediction_date, -6).isoformat(), "weight_kg": baseline_weight},
            {"date": prediction_date.isoformat(), "weight_kg": baseline_weight},
        ]
        return weights, "baseline_stability"
    if index == 4:
        patient["reduced_appetite"] = "yes"
        previous = baseline_weight / (
            1.0 - assumptions["limited_weight_loss_percent"] / 100.0
        )
        weights = [
            {"date": add_calendar_months(prediction_date, -6).isoformat(), "weight_kg": previous},
            {"date": prediction_date.isoformat(), "weight_kg": baseline_weight},
        ]
        return weights, "limited_loss_with_appetite"
    if index == 5:
        previous = baseline_weight / (
            1.0 - assumptions["supported_cachexia_weight_loss_percent"] / 100.0
        )
        weights = [
            {"date": add_calendar_months(prediction_date, -6).isoformat(), "weight_kg": previous},
            {"date": prediction_date.isoformat(), "weight_kg": baseline_weight},
        ]
        return weights, "supported_cachexia_pattern"
    if index == 6:
        patient["height_cm"] = assumptions["bmi_boundary_height_cm"]
        height_metres = patient["height_cm"] / 100.0
        baseline_weight = assumptions["bmi_boundary_value"] * height_metres**2
        return [
            {
                "date": add_calendar_months(prediction_date, -6).isoformat(),
                "weight_kg": baseline_weight
                / (
                    1.0
                    - assumptions["weight_loss_lower_boundary_percent"] / 100.0
                ),
            },
            {"date": prediction_date.isoformat(), "weight_kg": baseline_weight},
        ], "bmi_20_weight_loss_2_boundary"
    if index == 7:
        return [
            {
                "date": add_calendar_months(prediction_date, -6).isoformat(),
                "weight_kg": baseline_weight
                / (
                    1.0
                    - assumptions["weight_loss_upper_boundary_percent"] / 100.0
                ),
            },
            {"date": prediction_date.isoformat(), "weight_kg": baseline_weight},
        ], "weight_loss_5_boundary"
    return [], None


def generate_patients(
    count: int, seed: int, config_path: str | Path | None = None
) -> list[dict[str, Any]]:
    """Generate synthetic patients; the same seed and config produce identical data."""

    if count < 1:
        raise ValueError("count must be at least 1.")
    config = load_config(config_path)
    cohort = config["cohort"]
    relationships = config["simulation_relationships"]
    rng = random.Random(seed)
    start_date = date.fromisoformat(cohort["prediction_date_start"])
    patients = []
    for index in range(count):
        sex = _weighted_choice(rng, cohort["sex_probabilities"])
        height_config = cohort["height_cm"][sex]
        height = round(
            _bounded_gaussian(
                rng,
                height_config["mean"],
                height_config["sd"],
                height_config["minimum"],
                height_config["maximum"],
            ),
            1,
        )
        age_config = cohort["age"]
        age = round(
            rng.triangular(
                age_config["minimum"],
                age_config["maximum"],
                age_config["triangular_mode"],
            )
        )
        cancer_type = _weighted_choice(rng, cohort["cancer_type_probabilities"])
        stage = _weighted_choice(rng, cohort["stage_probabilities"])
        ecog_text = _weighted_choice(rng, cohort["ecog_probabilities"])
        ecog = None if ecog_text == "unknown" else int(ecog_text)
        sarcopenia = _weighted_choice(rng, cohort["sarcopenia_probabilities"])
        latent = (
            relationships["stage_latent_points"][stage]
            + relationships["ecog_latent_points"][ecog_text]
            + relationships["cancer_latent_points"][cancer_type]
            + rng.gauss(0, relationships["latent_random_sd"])
        )
        latent = min(
            relationships["latent_score_maximum"],
            max(relationships["latent_score_minimum"], latent),
        )
        if rng.random() < cohort["appetite_unknown_probability"]:
            appetite = "unknown"
        else:
            appetite_probability = _sigmoid(
                relationships["appetite_yes_logit_intercept"]
                + latent * relationships["appetite_yes_latent_multiplier"]
            )
            appetite = "yes" if rng.random() < appetite_probability else "no"
        bmi_config = cohort["bmi"]
        bmi = rng.triangular(
            bmi_config["minimum"], bmi_config["maximum"], bmi_config["triangular_mode"]
        )
        baseline_weight = bmi * (height / 100.0) ** 2
        # Redraw BMI rather than silently clipping an invalid generated weight.
        for _ in range(100):
            if cohort["weight_kg"]["minimum"] <= baseline_weight <= cohort["weight_kg"]["maximum"]:
                break
            bmi = rng.triangular(
                bmi_config["minimum"], bmi_config["maximum"], bmi_config["triangular_mode"]
            )
            baseline_weight = bmi * (height / 100.0) ** 2
        else:
            raise RuntimeError("Unable to generate a permitted baseline weight.")
        baseline_weight = round(baseline_weight, 3)
        prediction_date = start_date + timedelta(
            days=index % cohort["prediction_date_cycle_days"]
        )
        subtype = (
            _weighted_choice(rng, cohort["lung_subtype_probabilities"])
            if cancer_type == "lung"
            else None
        )
        patient: dict[str, Any] = {
            "patient_id": f"SYN-{seed:06d}-{index + 1:04d}",
            "prediction_date": prediction_date.isoformat(),
            "age": age,
            "sex": sex,
            "cancer_type": cancer_type,
            "cancer_subtype": subtype,
            "cancer_stage": stage,
            "height_cm": height,
            "ecog": ecog,
            "reduced_appetite": appetite,
            "sarcopenia": sarcopenia,
            "weights": [],
            "edge_case": None,
            "provenance": {
                "synthetic": True,
                "generator": "cachexia_poc.generator",
                "seed": seed,
                "config_version": config["metadata"]["config_version"],
                "clinical_validation": "none",
            },
        }
        weights, edge_case = _edge_case_override(
            index,
            patient,
            baseline_weight,
            prediction_date,
            config["edge_cases"],
        )
        if not weights:
            history_missing = rng.random() < cohort["insufficient_history_probability"]
            weights = []
            if not history_missing:
                monthly_history_loss = (
                    relationships["historical_monthly_loss_percent_intercept"]
                    + latent
                    * relationships["historical_monthly_loss_percent_latent_multiplier"]
                )
                for offset in cohort["history_month_offsets"]:
                    cumulative = monthly_history_loss * abs(offset)
                    historical_weight = baseline_weight / (1.0 - cumulative / 100.0)
                    if not cohort["historical_weight_kg"]["minimum"] <= historical_weight <= cohort["historical_weight_kg"]["maximum"]:
                        raise RuntimeError("Generated historical weight is outside configured bounds.")
                    weights.append(
                        {
                            "date": add_calendar_months(prediction_date, offset).isoformat(),
                            "weight_kg": round(historical_weight, 3),
                        }
                    )
            weights.append(
                {"date": prediction_date.isoformat(), "weight_kg": baseline_weight}
            )
        patient["edge_case"] = edge_case
        baseline_weight = float(weights[-1]["weight_kg"])
        monthly_future_loss = (
            relationships["future_monthly_loss_percent_intercept"]
            + latent * relationships["future_monthly_loss_percent_latent_multiplier"]
            + rng.gauss(0, relationships["future_monthly_loss_percent_random_sd"])
        )
        monthly_future_loss = min(
            relationships["monthly_loss_percent_maximum"],
            max(relationships["monthly_loss_percent_minimum"], monthly_future_loss),
        )
        weight_3m = baseline_weight * (1.0 - monthly_future_loss * 3 / 100.0)
        incremental_rate = monthly_future_loss * relationships["six_month_increment_multiplier"]
        weight_6m = weight_3m * (1.0 - incremental_rate * 3 / 100.0)
        for horizon, future_weight in ((3, weight_3m), (6, weight_6m)):
            if not cohort["historical_weight_kg"]["minimum"] <= future_weight <= cohort["historical_weight_kg"]["maximum"]:
                raise RuntimeError("Generated future weight is outside configured bounds.")
            weights.append(
                {
                    "date": add_calendar_months(prediction_date, horizon).isoformat(),
                    "weight_kg": round(future_weight, 3),
                }
            )
        patient["weights"] = weights
        predictors = calculate_predictors(
            patient, config["definitions"]["trajectory_epsilon_percent"]
        )
        patient["baseline_predictors"] = predictors
        pre_config = {
            "lower_weight_loss_percent_exclusive": config["definitions"][
                "precachexia_lower_weight_loss_percent_exclusive"
            ],
            "upper_weight_loss_percent_inclusive": config["definitions"][
                "precachexia_upper_weight_loss_percent_inclusive"
            ],
        }
        patient["outcome_3m"] = evaluate_horizon(patient, 3, pre_config)
        patient["outcome_6m"] = evaluate_horizon(patient, 6, pre_config)
        patient["simulated_risk_3m"] = _risk_output(
            patient, predictors, "three_month", config
        )
        patient["simulated_risk_6m"] = _risk_output(
            patient, predictors, "six_month", config
        )
        patients.append(patient)
    return patients


def write_json(
    patients: Iterable[dict[str, Any]], output_path: str | Path
) -> None:
    with Path(output_path).open("w", encoding="utf-8") as handle:
        json.dump(list(patients), handle, indent=2)
        handle.write("\n")


def write_csv(
    patients: Iterable[dict[str, Any]], output_path: str | Path
) -> None:
    rows = []
    for patient in patients:
        rows.append(
            {
                "patient_id": patient["patient_id"],
                "prediction_date": patient["prediction_date"],
                "age": patient["age"],
                "sex": patient["sex"],
                "cancer_type": patient["cancer_type"],
                "cancer_subtype": patient["cancer_subtype"],
                "cancer_stage": patient["cancer_stage"],
                "height_cm": patient["height_cm"],
                "ecog": "unknown" if patient["ecog"] is None else patient["ecog"],
                "reduced_appetite": patient["reduced_appetite"],
                "sarcopenia": patient["sarcopenia"],
                "weights_json": json.dumps(patient["weights"], separators=(",", ":")),
                "baseline_bmi": patient["baseline_predictors"]["bmi"],
                "baseline_weight_loss_percent": patient["baseline_predictors"][
                    "weight_loss_percent"
                ],
                "outcome_3m_cachexia": patient["outcome_3m"]["cachexia"],
                "outcome_3m_precachexia_candidate": patient["outcome_3m"][
                    "precachexia_candidate"
                ],
                "outcome_6m_cachexia": patient["outcome_6m"]["cachexia"],
                "outcome_6m_precachexia_candidate": patient["outcome_6m"][
                    "precachexia_candidate"
                ],
                "simulated_risk_3m": patient["simulated_risk_3m"]["probability"],
                "simulated_risk_6m": patient["simulated_risk_6m"]["probability"],
                "edge_case": patient["edge_case"],
                "synthetic": True,
                "config_version": patient["provenance"]["config_version"],
            }
        )
    if not rows:
        raise ValueError("Cannot write an empty cohort.")
    with Path(output_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
