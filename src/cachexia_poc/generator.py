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
from .outcomes import add_calendar_months, evaluate_baseline_status, evaluate_horizon

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


def _illustrative_category_output(
    patient: dict[str, Any],
    predictors: dict[str, Any],
    horizon_key: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    model = config["illustrative_category_model"]
    assumptions = model[horizon_key]
    horizon_months = 3 if horizon_key == "three_month" else 6
    missing: list[str] = []
    explanations: list[str] = []
    if patient["cancer_stage"] == "unknown":
        missing.append("cancer_stage_unknown")
        explanations.append("Cancer stage is unknown.")
    if patient["ecog"] is None:
        missing.append("ecog_unknown")
        explanations.append("Baseline ECOG is unknown.")
    if patient["reduced_appetite"] == "unknown":
        missing.append("reduced_appetite_unknown")
        explanations.append("Baseline reduced appetite is unknown.")
    if predictors["bmi"] is None:
        missing.append("bmi_unavailable")
        explanations.append(
            "BMI is unavailable because height or baseline weight is unavailable."
        )
    if predictors["weight_loss_percent"] is None:
        missing.append("baseline_weight_change_unavailable")
        explanations.append(
            "Baseline weight change is unavailable because eligible prior "
            "weight history is insufficient."
        )
    contract = model["output_contract"]
    common = {
        "horizon_months": horizon_months,
        "output_type": contract["output_type"],
        "basis": contract["basis"],
        "target_outcome": contract["target_outcome"],
        "unused_fields": contract["unused_fields"],
    }
    if (
        config["definitions"]["simulation_category_missing_predictor_policy"]
        == "withhold"
        and missing
    ):
        return {
            **common,
            "category": None,
            "status": "withheld_missing_required_baseline_predictors",
            "withholding_reasons": missing,
            "explanations": [
                f"{horizon_months}-month illustrative simulation category withheld."
            ]
            + explanations,
        }
    internal_value = float(assumptions["intercept"])
    factors: list[str] = []
    if patient["age"] > model["age_threshold_exclusive"]:
        internal_value += assumptions["age_over_55"]
        factors.append("age >55 simulation term")
    stage_term = assumptions["stage"][patient["cancer_stage"]]
    internal_value += stage_term
    if stage_term:
        factors.append(f"stage {patient['cancer_stage']} simulation term")
    ecog_key = "unknown" if patient["ecog"] is None else str(patient["ecog"])
    ecog_term = assumptions["ecog"][ecog_key]
    internal_value += ecog_term
    if ecog_term:
        factors.append(f"ECOG {ecog_key} simulation term")
    appetite_term = assumptions["appetite"][patient["reduced_appetite"]]
    internal_value += appetite_term
    if appetite_term:
        factors.append(f"appetite={patient['reduced_appetite']} simulation term")
    loss = predictors["weight_loss_percent"]
    if loss is not None and loss > 0:
        internal_value += loss * assumptions["baseline_weight_loss_per_percent"]
        factors.append(f"baseline weight loss {loss:.1f}% simulation term")
    bmi = predictors["bmi"]
    bmi_threshold = config["definitions"]["fearon_bmi_exclusive"]
    if bmi is not None and bmi < bmi_threshold:
        internal_value += assumptions["low_bmi_under_20"]
        factors.append(f"BMI <{bmi_threshold:g} simulation term")
    cancer_multiplier = config["simulation_relationships"][
        "cancer_risk_multipliers"
    ][patient["cancer_type"]]
    cancer_term = (
        cancer_multiplier - 1.0
    ) * assumptions["cancer_type_multiplier"]
    internal_value += cancer_term
    if cancer_term:
        factors.append(f"{patient['cancer_type']} simulation term")
    thresholds = model["internal_score_thresholds"]
    category = (
        "low"
        if internal_value < thresholds["low_upper_exclusive"]
        else "high"
        if internal_value >= thresholds["high_lower_inclusive"]
        else "moderate"
    )
    return {
        **common,
        "category": category,
        "status": contract["status"],
        "withholding_reasons": [],
        "explanations": [
            f"{horizon_months}-month illustrative simulation category based "
            "on baseline predictors only."
        ]
        + (factors or ["No non-intercept simulation terms were active."]),
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
            relationships["stage_risk_multipliers"][stage]
            * relationships["cancer_risk_multipliers"][cancer_type]
            - 1.0
            + relationships["ecog_latent_points"][ecog_text]
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
            else "not applicable"
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
            "follow_up_appetite_observations": [],
            "weights": [],
            "edge_case": None,
            "provenance": {
                "synthetic": True,
                "generator": "cachexia_poc.generator",
                "seed": seed,
                "config_version": config["metadata"]["config_version"],
                "schema_version": config["metadata"]["schema_version"],
                "schema_migration": (
                    "v1.1 adds dated follow-up appetite evidence, separates "
                    "baseline status from future outcomes, and replaces numeric "
                    "outputs with ordinal illustrative categories."
                ),
                "clinical_validation": "none",
                "precachexia_rule_status": config["definitions"][
                    "precachexia_rule_status"
                ],
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
        for horizon in cohort["future_horizon_months"]:
            if rng.random() < cohort["follow_up_appetite_unknown_probability"]:
                follow_up_appetite = "unknown"
            else:
                follow_up_appetite_probability = _sigmoid(
                    relationships["appetite_yes_logit_intercept"]
                    + latent * relationships["appetite_yes_latent_multiplier"]
                )
                follow_up_appetite = (
                    "yes"
                    if rng.random() < follow_up_appetite_probability
                    else "no"
                )
            patient["follow_up_appetite_observations"].append(
                {
                    "date": add_calendar_months(
                        prediction_date, horizon
                    ).isoformat(),
                    "reduced_appetite": follow_up_appetite,
                    "source": "synthetic_follow_up_observation",
                }
            )
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
        patient["baseline_criteria_status"] = evaluate_baseline_status(
            patient, predictors, pre_config
        )
        patient["outcome_3m"] = evaluate_horizon(patient, 3, pre_config)
        patient["outcome_6m"] = evaluate_horizon(patient, 6, pre_config)
        patient["illustrative_simulation_3m"] = _illustrative_category_output(
            patient, predictors, "three_month", config
        )
        patient["illustrative_simulation_6m"] = _illustrative_category_output(
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
                "follow_up_appetite_observations_json": json.dumps(
                    patient["follow_up_appetite_observations"],
                    separators=(",", ":"),
                ),
                "weights_json": json.dumps(patient["weights"], separators=(",", ":")),
                "baseline_bmi": patient["baseline_predictors"]["bmi"],
                "baseline_weight_loss_percent": patient["baseline_predictors"][
                    "weight_loss_percent"
                ],
                "baseline_cachexia_criteria_status": patient[
                    "baseline_criteria_status"
                ]["cachexia_criteria_status"],
                "baseline_precachexia_candidate_status": patient[
                    "baseline_criteria_status"
                ]["precachexia_candidate_status"],
                "outcome_3m_threshold_based_cachexia_status": patient[
                    "outcome_3m"
                ]["threshold_based_cachexia_status"],
                "outcome_3m_fearon_classification": patient["outcome_3m"][
                    "fearon_classification"
                ],
                "outcome_3m_interval_days": patient["outcome_3m"][
                    "outcome_interval_days"
                ],
                "outcome_3m_precachexia_candidate_status": patient["outcome_3m"][
                    "precachexia_candidate_status"
                ],
                "outcome_3m_basis": patient["outcome_3m"]["outcome_basis"],
                "outcome_6m_threshold_based_cachexia_status": patient[
                    "outcome_6m"
                ]["threshold_based_cachexia_status"],
                "outcome_6m_fearon_classification": patient["outcome_6m"][
                    "fearon_classification"
                ],
                "outcome_6m_interval_days": patient["outcome_6m"][
                    "outcome_interval_days"
                ],
                "outcome_6m_precachexia_candidate_status": patient["outcome_6m"][
                    "precachexia_candidate_status"
                ],
                "outcome_6m_basis": patient["outcome_6m"]["outcome_basis"],
                "illustrative_simulation_category_3m": patient[
                    "illustrative_simulation_3m"
                ]["category"],
                "illustrative_simulation_category_3m_basis": patient[
                    "illustrative_simulation_3m"
                ]["basis"],
                "illustrative_simulation_category_3m_status": patient[
                    "illustrative_simulation_3m"
                ]["status"],
                "illustrative_simulation_category_3m_target_outcome": patient[
                    "illustrative_simulation_3m"
                ]["target_outcome"],
                "illustrative_simulation_category_6m": patient[
                    "illustrative_simulation_6m"
                ]["category"],
                "illustrative_simulation_category_6m_basis": patient[
                    "illustrative_simulation_6m"
                ]["basis"],
                "illustrative_simulation_category_6m_status": patient[
                    "illustrative_simulation_6m"
                ]["status"],
                "illustrative_simulation_category_6m_target_outcome": patient[
                    "illustrative_simulation_6m"
                ]["target_outcome"],
                "edge_case": patient["edge_case"],
                "synthetic": True,
                "config_version": patient["provenance"]["config_version"],
                "schema_version": patient["provenance"]["schema_version"],
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
