from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from cachexia_poc.config import load_simulation_config
from cachexia_poc.generator import _risk_output
from cachexia_poc.outcomes import evaluate_horizon

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "clinical_logic_cases.v1.json"


class ClinicalLogicAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.config = load_simulation_config()

    def test_cases_are_traceable_and_not_claimed_as_clinically_approved(self):
        metadata = self.fixture["metadata"]
        self.assertIn("does not establish clinical validity", metadata["warning"])
        self.assertIn("pending", metadata["clinical_approval"])
        for case in self.fixture["classification_cases"]:
            self.assertTrue(case["source"])
            self.assertIn(
                case["status"],
                {
                    "documented_requirement",
                    "project_operationalisation_pending_review",
                    "subsequent_project_decision_pending_review",
                },
            )
        self.assertEqual(
            self.fixture["risk_case"]["status"],
            "simulation_assumption_not_clinically_validated",
        )

    def test_python_classifications_match_the_decision_table(self):
        for case in self.fixture["classification_cases"]:
            with self.subTest(case=case["id"]):
                patient = {
                    "patient_id": f"TEST-{case['id']}",
                    "prediction_date": "2026-01-31",
                    "age": 60,
                    "sex": "female",
                    "cancer_type": "colorectal",
                    "cancer_subtype": None,
                    "cancer_stage": "III",
                    "height_cm": case["height_cm"],
                    "ecog": 2,
                    "reduced_appetite": case["appetite"],
                    "sarcopenia": case["sarcopenia"],
                    "weights": [
                        {
                            "date": "2026-01-31",
                            "weight_kg": case["baseline_weight_kg"],
                        },
                        {
                            "date": "2026-04-30",
                            "weight_kg": case["outcome_weight_kg"],
                        },
                    ],
                }
                result = evaluate_horizon(patient, 3)
                self.assertEqual(result["cachexia"], case["expected_cachexia"])
                self.assertEqual(
                    result["precachexia_candidate"],
                    case["expected_precachexia"],
                )

    def test_python_risk_output_matches_documented_arithmetic(self):
        case = self.fixture["risk_case"]
        for horizon in ("three_month", "six_month"):
            with self.subTest(horizon=horizon):
                result = _risk_output(
                    case["patient"],
                    case["predictors"],
                    horizon,
                    self.config,
                )
                expected = case["expected"][horizon]
                self.assertTrue(
                    math.isclose(result["score"], expected["score"], abs_tol=1e-12)
                )
                self.assertTrue(
                    math.isclose(
                        result["probability"],
                        expected["probability"],
                        abs_tol=1e-12,
                    )
                )
                self.assertEqual(result["band"], expected["band"])
                self.assertIn("not clinically validated", result["warning"])

    def test_configuration_matches_recorded_clinical-reviewer_assumptions(self):
        expected = self.fixture["configuration_expectations"]
        self.assertEqual(self.config["cohort"]["age"], expected["age"])
        self.assertEqual(
            self.config["cohort"]["ecog_probabilities"],
            expected["ecog_probabilities"],
        )
        relationships = self.config["simulation_relationships"]
        self.assertEqual(
            relationships["cancer_risk_multipliers"],
            expected["cancer_risk_multipliers"],
        )
        self.assertEqual(
            relationships["stage_risk_multipliers"],
            expected["stage_risk_multipliers"],
        )


if __name__ == "__main__":
    unittest.main()
