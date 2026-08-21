from __future__ import annotations

import copy
import unittest
from datetime import date
from unittest.mock import patch

from cachexia_poc.outcomes import (
    add_calendar_months,
    evaluate_baseline_status,
    evaluate_horizon,
)
from tests.test_core import patient


class HorizonOutcomeTests(unittest.TestCase):
    def test_calendar_month_clamps_month_end(self):
        self.assertEqual(add_calendar_months("2026-01-31", 3), date(2026, 4, 30))
        self.assertEqual(add_calendar_months("2024-11-30", 3), date(2025, 2, 28))

    def test_exact_horizon_is_included(self):
        value = patient(
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 75},
                {"date": "2026-05-01", "weight_kg": 40},
            ],
            sarcopenia="no",
        )
        result = evaluate_horizon(value, 3)
        self.assertEqual(result["outcome_weight_date"], "2026-04-30")
        self.assertEqual(result["threshold_based_cachexia_status"], "yes")

    def test_day_after_horizon_is_excluded(self):
        value = patient(
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-05-01", "weight_kg": 40},
            ]
        )
        self.assertEqual(
            evaluate_horizon(value, 3)["threshold_based_cachexia_status"],
            "unknown",
        )

    def test_three_and_six_month_outcomes_are_separate(self):
        value = patient(
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 80},
                {"date": "2026-07-31", "weight_kg": 72},
            ],
            sarcopenia="no",
        )
        self.assertEqual(
            evaluate_horizon(value, 3)["threshold_based_cachexia_status"], "no"
        )
        self.assertEqual(
            evaluate_horizon(value, 6)["threshold_based_cachexia_status"], "yes"
        )

    def test_changing_six_month_data_cannot_change_three_month_label(self):
        value = patient(
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 79},
                {"date": "2026-07-31", "weight_kg": 78},
            ],
            sarcopenia="no",
        )
        changed = copy.deepcopy(value)
        changed["weights"][-1]["weight_kg"] = 40
        self.assertEqual(evaluate_horizon(value, 3), evaluate_horizon(changed, 3))

    def test_fearon_strict_boundaries(self):
        base = 80.0
        exactly_five = patient(
            height_cm=180,
            sarcopenia="no",
            weights=[
                {"date": "2026-01-31", "weight_kg": base},
                {"date": "2026-04-30", "weight_kg": base * 0.95},
            ],
        )
        over_five = copy.deepcopy(exactly_five)
        over_five["weights"][1]["weight_kg"] = base * 0.949
        self.assertEqual(
            evaluate_horizon(exactly_five, 3)["threshold_based_cachexia_status"],
            "unknown",
        )
        self.assertEqual(
            evaluate_horizon(over_five, 3)["threshold_based_cachexia_status"],
            "yes",
        )

    def test_exactly_two_percent_does_not_enter_conditional_branches(self):
        value = patient(
            height_cm=180,
            sarcopenia="yes",
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 78.4},
            ],
        )
        self.assertEqual(
            evaluate_horizon(value, 3)["threshold_based_cachexia_status"], "no"
        )

    def test_bmi_below_20_branch_and_exact_bmi_20_boundary(self):
        below = patient(
            height_cm=200,
            sarcopenia="no",
            weights=[
                {"date": "2026-01-31", "weight_kg": 82.5},
                {"date": "2026-04-30", "weight_kg": 79.9},
            ],
        )
        exact = copy.deepcopy(below)
        exact["weights"][0]["weight_kg"] = 82.5
        exact["weights"][1]["weight_kg"] = 80.0
        self.assertEqual(
            evaluate_horizon(below, 3)["threshold_based_cachexia_status"], "yes"
        )
        self.assertEqual(
            evaluate_horizon(exact, 3)["threshold_based_cachexia_status"],
            "unknown",
        )

    def test_disabled_sarcopenia_branch_preserves_unknown_status(self):
        value = patient(
            height_cm=180,
            sarcopenia="unknown",
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 77.6},
            ],
        )
        result = evaluate_horizon(value, 3)
        self.assertEqual(result["threshold_based_cachexia_status"], "unknown")
        self.assertEqual(result["precachexia_candidate_status"], "unknown")
        explicitly_yes = copy.deepcopy(value)
        explicitly_yes["sarcopenia"] = "yes"
        self.assertEqual(
            evaluate_horizon(explicitly_yes, 3)["threshold_based_cachexia_status"],
            "unknown",
        )
        explicitly_no = copy.deepcopy(value)
        explicitly_no["sarcopenia"] = "no"
        self.assertEqual(
            evaluate_horizon(explicitly_no, 3)["threshold_based_cachexia_status"],
            "unknown",
        )
        self.assertEqual(
            result["provenance"]["sarcopenia_evidence"],
            "future_use_pending_clinical_definition",
        )
        self.assertTrue(
            any(
                "disabled pending a clinical definition" in explanation
                for explanation in result["explanations"]
            )
        )

    def test_baseline_sarcopenia_never_becomes_future_evidence(self):
        weights = [
            {"date": "2026-01-31", "weight_kg": 80},
            {"date": "2026-04-30", "weight_kg": 77.6},
        ]
        with patch(
            "cachexia_poc.outcomes._SARCOPENIA_BRANCH_ENABLED",
            True,
        ):
            results = [
                evaluate_horizon(
                    patient(
                        height_cm=180,
                        sarcopenia=sarcopenia,
                        weights=weights,
                    ),
                    3,
                )
                for sarcopenia in ("yes", "no", "unknown")
            ]
        self.assertEqual(
            {
                result["threshold_based_cachexia_status"]
                for result in results
            },
            {"unknown"},
        )
        self.assertEqual(
            {
                result["provenance"]["sarcopenia_evidence"]
                for result in results
            },
            {"future_use_pending_clinical_definition"},
        )

    def test_sarcopenia_does_not_decide_when_bmi_is_unknown(self):
        value = patient(
            height_cm=None,
            sarcopenia="yes",
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 77.6},
            ],
        )
        self.assertEqual(
            evaluate_horizon(value, 3)["threshold_based_cachexia_status"],
            "unknown",
        )

    def test_provisional_precachexia_and_unknown_appetite(self):
        weights = [
            {"date": "2026-01-31", "weight_kg": 80},
            {"date": "2026-04-30", "weight_kg": 78.8},
        ]
        yes = evaluate_horizon(
            patient(
                weights=weights,
                reduced_appetite="no",
                sarcopenia="no",
                follow_up_appetite_observations=[
                    {
                        "date": "2026-04-30",
                        "reduced_appetite": "yes",
                        "source": "synthetic_follow_up_observation",
                    }
                ],
            ),
            3,
        )
        unknown = evaluate_horizon(
            patient(
                weights=weights,
                reduced_appetite="yes",
                sarcopenia="no",
                follow_up_appetite_observations=[],
            ),
            3,
        )
        self.assertEqual(yes["precachexia_candidate_status"], "yes")
        self.assertEqual(unknown["precachexia_candidate_status"], "unknown")
        self.assertEqual(
            unknown["provenance"]["appetite_evidence"],
            "unavailable_no_baseline_carry_forward",
        )

    def test_baseline_appetite_cannot_change_future_label_without_follow_up(self):
        weights = [
            {"date": "2026-01-31", "weight_kg": 80},
            {"date": "2026-04-30", "weight_kg": 78.8},
        ]
        labels = {
            evaluate_horizon(
                patient(
                    weights=weights,
                    reduced_appetite=appetite,
                    sarcopenia="no",
                    follow_up_appetite_observations=[],
                ),
                3,
            )["precachexia_candidate_status"]
            for appetite in ("yes", "no", "unknown")
        }
        self.assertEqual(labels, {"unknown"})

    def test_outcome_provenance_and_current_future_framing_are_explicit(self):
        value = patient(
            sarcopenia="yes",
            follow_up_appetite_observations=[
                {
                    "date": "2026-04-30",
                    "reduced_appetite": "no",
                    "source": "synthetic_follow_up_observation",
                }
            ],
            weights=[
                {"date": "2025-07-31", "weight_kg": 84},
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 78},
            ],
        )
        current = evaluate_baseline_status(value)
        future = evaluate_horizon(value, 3)
        self.assertEqual(current["basis"], "baseline_derived_current_status")
        self.assertEqual(future["outcome_basis"], "observed_synthetic_follow_up")
        self.assertEqual(
            future["status"],
            "research_only_threshold_based_outcome_not_fearon_classification",
        )
        self.assertFalse(future["fearon_classification"])
        self.assertEqual(future["outcome_interval_days"], 89)
        self.assertIn("direction and window length", future["fearon_2011_comparison"])

        six_month = evaluate_horizon(value, 6)
        self.assertEqual(
            six_month["status"],
            "prospective_research_endpoint_not_fearon_classification_or_diagnosis",
        )
        self.assertFalse(six_month["fearon_classification"])
        self.assertIn("not a Fearon classification", six_month["fearon_2011_comparison"])


if __name__ == "__main__":
    unittest.main()
