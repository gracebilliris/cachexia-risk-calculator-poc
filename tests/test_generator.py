from __future__ import annotations

import csv
import unittest
import json
from pathlib import Path

import copy

from cachexia_poc.generator import (
    _illustrative_category_output,
    generate_patients,
    load_config,
)
from cachexia_poc.outcomes import add_calendar_months

ROOT = Path(__file__).resolve().parents[1]


class GeneratorTests(unittest.TestCase):
    def test_seed_is_reproducible(self):
        self.assertEqual(generate_patients(12, 42), generate_patients(12, 42))
        self.assertNotEqual(generate_patients(12, 42), generate_patients(12, 43))

    def test_every_patient_has_explicit_dates_and_separate_outputs(self):
        for value in generate_patients(20, 7):
            self.assertRegex(value["prediction_date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIn("outcome_3m", value)
            self.assertIn("outcome_6m", value)
            self.assertIn("baseline_criteria_status", value)
            self.assertIn("illustrative_simulation_3m", value)
            self.assertIn("illustrative_simulation_6m", value)
            dates = {measurement["date"] for measurement in value["weights"]}
            self.assertIn(
                add_calendar_months(value["prediction_date"], 3).isoformat(), dates
            )
            self.assertIn(
                add_calendar_months(value["prediction_date"], 6).isoformat(), dates
            )
            appetite_dates = {
                observation["date"]
                for observation in value["follow_up_appetite_observations"]
            }
            self.assertIn(
                add_calendar_months(value["prediction_date"], 3).isoformat(),
                appetite_dates,
            )
            self.assertIn(
                add_calendar_months(value["prediction_date"], 6).isoformat(),
                appetite_dates,
            )
            self.assertTrue(
                all(
                    observation["source"]
                    == "synthetic_follow_up_observation"
                    for observation in value["follow_up_appetite_observations"]
                )
            )
            for outcome_name in ("outcome_3m", "outcome_6m"):
                outcome = value[outcome_name]
                self.assertFalse(outcome["fearon_classification"])
                self.assertGreater(outcome["outcome_interval_days"], 0)

    def test_six_month_process_extends_three_month_process(self):
        for value in generate_patients(20, 11):
            weights = {
                measurement["date"]: measurement["weight_kg"]
                for measurement in value["weights"]
            }
            date_3m = add_calendar_months(value["prediction_date"], 3).isoformat()
            date_6m = add_calendar_months(value["prediction_date"], 6).isoformat()
            self.assertIn(date_3m, weights)
            self.assertIn(date_6m, weights)
            self.assertEqual(value["outcome_3m"]["outcome_weight_date"], date_3m)
            self.assertEqual(value["outcome_6m"]["outcome_weight_date"], date_6m)
            self.assertEqual(
                value["outcome_3m"]["follow_up_appetite_date"], date_3m
            )
            self.assertEqual(
                value["outcome_6m"]["follow_up_appetite_date"], date_6m
            )

    def test_expected_edge_case_mix_is_present(self):
        patients = generate_patients(12, 99)
        edge_cases = {value["edge_case"] for value in patients}
        self.assertIn("insufficient_history", edge_cases)
        self.assertIn("baseline_weight_gain", edge_cases)
        self.assertIn("limited_loss_with_appetite", edge_cases)
        self.assertIn("weight_loss_5_boundary", edge_cases)
        insufficient = next(
            value for value in patients
            if value["edge_case"] == "insufficient_history"
        )
        self.assertIsNone(insufficient["illustrative_simulation_3m"]["category"])
        self.assertIn(
            "baseline_weight_change_unavailable",
            insufficient["illustrative_simulation_3m"]["withholding_reasons"],
        )

    def test_sample_scale_contains_all_illustrative_categories(self):
        values = generate_patients(120, 20260820)
        self.assertEqual(
            {
                item["illustrative_simulation_3m"]["category"]
                for item in values
            },
            {"low", "moderate", "high", None},
        )
        self.assertEqual(
            {
                item["illustrative_simulation_6m"]["category"]
                for item in values
            },
            {"low", "moderate", "high", None},
        )
        for item in values:
            output = item["illustrative_simulation_3m"]
            self.assertEqual(output["output_type"], "illustrative_simulation_category")
            self.assertEqual(
                output["target_outcome"],
                "not_defined_pending_clinical_review",
            )
            self.assertTrue(output["explanations"])
            self.assertNotIn("probability", output)
            self.assertNotIn("score", output)

    def test_sex_subtype_and_sarcopenia_are_unused_in_category(self):
        item = next(
            value
            for value in generate_patients(30, 17)
            if value["illustrative_simulation_3m"]["category"] is not None
        )
        config = load_config()
        baseline = _illustrative_category_output(
            item, item["baseline_predictors"], "three_month", config
        )
        changed = copy.deepcopy(item)
        changed["sex"] = "unknown"
        changed["cancer_subtype"] = "unknown"
        changed["sarcopenia"] = "yes" if item["sarcopenia"] != "yes" else "no"
        self.assertEqual(
            baseline,
            _illustrative_category_output(
                changed, changed["baseline_predictors"], "three_month", config
            ),
        )

    def test_each_missing_required_baseline_value_withholds_category(self):
        item = next(
            value
            for value in generate_patients(40, 31)
            if value["illustrative_simulation_3m"]["category"] is not None
        )
        config = load_config()
        cases = (
            ("cancer_stage", "unknown", None, "cancer_stage_unknown"),
            ("ecog", None, None, "ecog_unknown"),
            (
                "reduced_appetite",
                "unknown",
                None,
                "reduced_appetite_unknown",
            ),
            ("predictor:bmi", None, "bmi", "bmi_unavailable"),
            (
                "predictor:weight_loss_percent",
                None,
                "weight_loss_percent",
                "baseline_weight_change_unavailable",
            ),
        )
        for field, value, predictor_field, expected_reason in cases:
            with self.subTest(field=field):
                changed = copy.deepcopy(item)
                predictors = copy.deepcopy(item["baseline_predictors"])
                if predictor_field:
                    predictors[predictor_field] = value
                else:
                    changed[field] = value
                output = _illustrative_category_output(
                    changed, predictors, "three_month", config
                )
                self.assertIsNone(output["category"])
                self.assertIn(expected_reason, output["withholding_reasons"])

    def test_versioned_exports_use_only_ordinal_category_contract(self):
        patients = json.loads(
            (ROOT / "data" / "synthetic_patients.v1.json").read_text(
                encoding="utf-8"
            )
        )
        for patient in patients:
            for field in (
                "illustrative_simulation_3m",
                "illustrative_simulation_6m",
            ):
                output = patient[field]
                self.assertNotIn("probability", output)
                self.assertNotIn("percentage", output)
                self.assertNotIn("score", output)
                self.assertIn(
                    output["category"],
                    {"low", "moderate", "high", None},
                )
        with (ROOT / "data" / "synthetic_patients.v1.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            reader = csv.DictReader(handle)
            folded_headers = [header.casefold() for header in reader.fieldnames or []]
            self.assertIn(
                "outcome_3m_interval_days",
                reader.fieldnames or [],
            )
            self.assertIn(
                "outcome_6m_fearon_classification",
                reader.fieldnames or [],
            )
            self.assertIn(
                "illustrative_simulation_category_3m_target_outcome",
                reader.fieldnames or [],
            )
            self.assertFalse(
                any(
                    forbidden in header
                    for forbidden in ("probability", "score", "simulated_risk")
                    for header in folded_headers
                )
            )
            self.assertTrue(
                all(
                    row["illustrative_simulation_category_3m"]
                    in {"low", "moderate", "high", ""}
                    for row in reader
                )
            )
        summary = json.loads(
            (ROOT / "data" / "distribution_summary.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("illustrative_simulation_category_3m", summary)
        self.assertIn("baseline_cachexia_criteria_status", summary)
        self.assertIn(
            "baseline_provisional_early_risk_candidate_status",
            summary,
        )
        self.assertNotIn("risk_3m_band", summary)


if __name__ == "__main__":
    unittest.main()
