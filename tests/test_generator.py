from __future__ import annotations

import unittest

from cachexia_poc.generator import generate_patients
from cachexia_poc.outcomes import add_calendar_months


class GeneratorTests(unittest.TestCase):
    def test_seed_is_reproducible(self):
        self.assertEqual(generate_patients(12, 42), generate_patients(12, 42))
        self.assertNotEqual(generate_patients(12, 42), generate_patients(12, 43))

    def test_every_patient_has_explicit_dates_and_separate_outputs(self):
        for value in generate_patients(20, 7):
            self.assertRegex(value["prediction_date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIn("outcome_3m", value)
            self.assertIn("outcome_6m", value)
            self.assertIn("simulated_risk_3m", value)
            self.assertIn("simulated_risk_6m", value)
            dates = {measurement["date"] for measurement in value["weights"]}
            self.assertIn(
                add_calendar_months(value["prediction_date"], 3).isoformat(), dates
            )
            self.assertIn(
                add_calendar_months(value["prediction_date"], 6).isoformat(), dates
            )

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
        self.assertIsNone(insufficient["simulated_risk_3m"]["probability"])
        self.assertEqual(insufficient["simulated_risk_3m"]["band"], "unknown")

    def test_sample_scale_contains_all_simulated_risk_bands(self):
        values = generate_patients(120, 20260820)
        self.assertEqual(
            {item["simulated_risk_3m"]["band"] for item in values},
            {"low", "medium", "high", "unknown"},
        )
        self.assertEqual(
            {item["simulated_risk_6m"]["band"] for item in values},
            {"low", "medium", "high", "unknown"},
        )
        for item in values:
            self.assertIn("not clinically validated", item["simulated_risk_3m"]["warning"])
            self.assertTrue(item["simulated_risk_3m"]["explanation"])


if __name__ == "__main__":
    unittest.main()
