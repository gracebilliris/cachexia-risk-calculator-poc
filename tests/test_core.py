from __future__ import annotations

import copy
import unittest

from cachexia_poc.core import (
    PatientValidationError,
    calculate_predictors,
    select_baseline_weight,
    validate_patient,
)


def patient(**overrides):
    value = {
        "patient_id": "SYN-TEST-001",
        "prediction_date": "2026-01-31",
        "age": 65,
        "sex": "female",
        "cancer_type": "lung",
        "cancer_subtype": "NSCLC",
        "cancer_stage": "III",
        "height_cm": 160.0,
        "ecog": 2,
        "reduced_appetite": "yes",
        "sarcopenia": "unknown",
        "weights": [
            {"date": "2025-07-31", "weight_kg": 80.0},
            {"date": "2026-01-31", "weight_kg": 72.0},
        ],
    }
    value.update(overrides)
    return value


class CoreCalculationTests(unittest.TestCase):
    def test_bmi_weight_loss_interval_and_rates(self):
        result = calculate_predictors(patient())
        self.assertAlmostEqual(result["bmi"], 28.125)
        self.assertAlmostEqual(result["weight_loss_percent"], 10.0)
        self.assertEqual(result["interval_days"], 184)
        self.assertAlmostEqual(
            result["weight_loss_kg_per_month"], 8 / (184 / 30.4375)
        )
        self.assertAlmostEqual(
            result["weight_loss_percentage_points_per_month"],
            10 / (184 / 30.4375),
        )
        self.assertEqual(result["trajectory"], "loss")

    def test_weight_gain_has_negative_loss_and_gain_trajectory(self):
        result = calculate_predictors(
            patient(
                weights=[
                    {"date": "2025-10-31", "weight_kg": 70},
                    {"date": "2026-01-31", "weight_kg": 73},
                ]
            )
        )
        self.assertLess(result["weight_loss_percent"], 0)
        self.assertLess(result["weight_loss_kg_per_month"], 0)
        self.assertEqual(result["trajectory"], "gain")

    def test_one_measurement_returns_not_calculable_change(self):
        result = calculate_predictors(
            patient(weights=[{"date": "2026-01-31", "weight_kg": 72}])
        )
        self.assertIsNotNone(result["bmi"])
        self.assertIsNone(result["weight_loss_percent"])
        self.assertIsNone(result["interval_days"])
        self.assertEqual(result["trajectory"], "unknown")

    def test_missing_height_preserves_unknown_bmi(self):
        result = calculate_predictors(patient(height_cm=None))
        self.assertIsNone(result["bmi"])
        self.assertAlmostEqual(result["weight_loss_percent"], 10)

    def test_duplicate_baseline_timestamp_uses_last_input_record(self):
        selected = select_baseline_weight(
            [
                {"date": "2026-01-31", "weight_kg": 72},
                {"date": "2026-01-31", "weight_kg": 71},
            ],
            "2026-01-31",
        )
        self.assertEqual(selected["weight_kg"], 71)

    def test_equal_timestamps_do_not_create_zero_interval(self):
        result = calculate_predictors(
            patient(
                weights=[
                    {"date": "2026-01-31", "weight_kg": 72},
                    {"date": "2026-01-31", "weight_kg": 71},
                ]
            )
        )
        self.assertIsNone(result["interval_days"])
        self.assertIsNone(result["weight_loss_percent"])

    def test_irregular_interval_uses_actual_days(self):
        result = calculate_predictors(
            patient(
                weights=[
                    {"date": "2025-12-17", "weight_kg": 80},
                    {"date": "2026-01-31", "weight_kg": 76},
                ]
            )
        )
        self.assertEqual(result["interval_days"], 45)
        self.assertAlmostEqual(
            result["weight_loss_kg_per_month"], 4 / (45 / 30.4375)
        )

    def test_post_prediction_measurements_cannot_change_predictors(self):
        original = patient()
        changed_future = copy.deepcopy(original)
        changed_future["weights"].extend(
            [
                {"date": "2026-02-01", "weight_kg": 25},
                {"date": "2026-08-01", "weight_kg": 160},
            ]
        )
        self.assertEqual(
            calculate_predictors(original), calculate_predictors(changed_future)
        )

    def test_invalid_values_are_rejected_not_corrected(self):
        with self.assertRaisesRegex(PatientValidationError, "140-200"):
            validate_patient(patient(height_cm=95))
        with self.assertRaisesRegex(PatientValidationError, "yes, no, or unknown"):
            validate_patient(patient(reduced_appetite=""))


if __name__ == "__main__":
    unittest.main()
