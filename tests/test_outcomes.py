from __future__ import annotations

import copy
import unittest
from datetime import date

from cachexia_poc.outcomes import add_calendar_months, evaluate_horizon
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
        self.assertEqual(result["cachexia"], "yes")

    def test_day_after_horizon_is_excluded(self):
        value = patient(
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-05-01", "weight_kg": 40},
            ]
        )
        self.assertEqual(evaluate_horizon(value, 3)["cachexia"], "unknown")

    def test_three_and_six_month_outcomes_are_separate(self):
        value = patient(
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 80},
                {"date": "2026-07-31", "weight_kg": 72},
            ],
            sarcopenia="no",
        )
        self.assertEqual(evaluate_horizon(value, 3)["cachexia"], "no")
        self.assertEqual(evaluate_horizon(value, 6)["cachexia"], "yes")

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
        self.assertEqual(evaluate_horizon(exactly_five, 3)["cachexia"], "no")
        self.assertEqual(evaluate_horizon(over_five, 3)["cachexia"], "yes")

    def test_exactly_two_percent_does_not_enter_conditional_branches(self):
        value = patient(
            height_cm=180,
            sarcopenia="yes",
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 78.4},
            ],
        )
        self.assertEqual(evaluate_horizon(value, 3)["cachexia"], "no")

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
        self.assertEqual(evaluate_horizon(below, 3)["cachexia"], "yes")
        self.assertEqual(evaluate_horizon(exact, 3)["cachexia"], "no")

    def test_sarcopenia_is_retained_but_not_used_in_v1(self):
        value = patient(
            height_cm=180,
            sarcopenia="unknown",
            weights=[
                {"date": "2026-01-31", "weight_kg": 80},
                {"date": "2026-04-30", "weight_kg": 77.6},
            ],
        )
        result = evaluate_horizon(value, 3)
        self.assertEqual(result["cachexia"], "no")
        explicitly_yes = copy.deepcopy(value)
        explicitly_yes["sarcopenia"] = "yes"
        self.assertEqual(evaluate_horizon(explicitly_yes, 3)["cachexia"], "no")

    def test_provisional_precachexia_and_unknown_appetite(self):
        weights = [
            {"date": "2026-01-31", "weight_kg": 80},
            {"date": "2026-04-30", "weight_kg": 78.8},
        ]
        yes = evaluate_horizon(
            patient(weights=weights, reduced_appetite="yes", sarcopenia="no"), 3
        )
        unknown = evaluate_horizon(
            patient(weights=weights, reduced_appetite="unknown", sarcopenia="no"), 3
        )
        self.assertEqual(yes["precachexia_candidate"], "yes")
        self.assertEqual(unknown["precachexia_candidate"], "unknown")


if __name__ == "__main__":
    unittest.main()
