from __future__ import annotations

import itertools
import json
import unittest
from pathlib import Path

from openpyxl import load_workbook

from cachexia_poc.outcomes import (
    DEFAULT_PRECACHEXIA_CONFIG,
    _fearon_status,
    _precachexia_status,
)
from scripts.build_clinical_logic_review import (
    APPETITE_STATES,
    BMI_STATES,
    LOSS_STATES,
    SARCOPENIA_STATES,
)

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "data" / "clinical_logic_matrix.v1.json"
WORKBOOK_PATH = ROOT / "excel" / "clinical_logic_review_matrix.v1.xlsx"


class ClinicalLogicMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.payload["cases"]
        cls.workbook = load_workbook(WORKBOOK_PATH, data_only=False)

    def test_matrix_contains_every_cartesian_combination_once(self):
        expected = set(
            itertools.product(
                (name for name, _ in LOSS_STATES),
                (name for name, _ in BMI_STATES),
                SARCOPENIA_STATES,
                APPETITE_STATES,
            )
        )
        actual = {
            (
                case["weight_loss_state"],
                case["bmi_state"],
                case["sarcopenia"],
                case["reduced_appetite"],
            )
            for case in self.cases
        }
        self.assertEqual(len(self.cases), 324)
        self.assertEqual(len({case["case_id"] for case in self.cases}), 324)
        self.assertEqual(actual, expected)
        self.assertEqual(self.payload["metadata"]["case_count"], 324)

    def test_all_matrix_expectations_match_python_production_logic(self):
        for case in self.cases:
            with self.subTest(case=case["case_id"]):
                loss = case["weight_loss_percent"]
                if loss is None:
                    cachexia, early_risk = "unknown", "unknown"
                else:
                    cachexia, _ = _fearon_status(
                        loss,
                        case["bmi"],
                        case["sarcopenia"],
                    )
                    early_risk, _ = _precachexia_status(
                        loss,
                        case["reduced_appetite"],
                        cachexia,
                        DEFAULT_PRECACHEXIA_CONFIG,
                    )
                self.assertEqual(cachexia, case["expected_cachexia"])
                self.assertEqual(
                    early_risk,
                    case["expected_early_risk"],
                )

    def test_review_workbook_contains_all_cases_and_decision_controls(self):
        self.assertEqual(
            self.workbook.sheetnames,
            [
                "START HERE",
                "Key Scenarios",
                "Review Decisions",
                "Full Logic Matrix",
                "Risk Assumptions",
            ],
        )
        scenarios = self.workbook["Key Scenarios"]
        self.assertEqual(scenarios.max_row, 19)
        self.assertEqual(scenarios["A8"].value, "No weight loss")
        self.assertIn("Loss over 5%", [scenarios.cell(row, 1).value for row in range(8, 20)])
        self.assertIn("J8:J19", str(list(scenarios.data_validations.dataValidation)[0].sqref))

        matrix = self.workbook["Full Logic Matrix"]
        self.assertIn("NOT FOR CLINICAL USE", matrix["A4"].value)
        self.assertEqual(matrix.max_row, 331)
        self.assertEqual(matrix["A8"].value, "LOGIC-001")
        self.assertEqual(matrix["A331"].value, "LOGIC-324")
        validations = list(matrix.data_validations.dataValidation)
        self.assertEqual(len(validations), 1)
        self.assertIn("agree", validations[0].formula1)
        self.assertIn("L8:L331", str(validations[0].sqref))

    def test_risk_terms_are_labelled_as_unvalidated_assumptions(self):
        sheet = self.workbook["Risk Assumptions"]
        statuses = {
            sheet.cell(row, 5).value
            for row in range(8, sheet.max_row + 1)
            if isinstance(sheet.cell(row, 4).value, (int, float))
            and sheet.cell(row, 5).value
        }
        self.assertTrue(statuses)
        self.assertTrue(
            all(
                "not clinically validated" in status
                or "not a relative risk" in status
                for status in statuses
            )
        )

    def test_workbook_contains_no_named_reviewers(self):
        blocked = ("Mari" + "ana", "Nami" + "tha")
        for sheet in self.workbook.worksheets:
            for row in sheet.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str):
                        self.assertFalse(
                            any(name.casefold() in cell.value.casefold() for name in blocked),
                            f"Named reviewer found in {sheet.title}!{cell.coordinate}",
                        )


if __name__ == "__main__":
    unittest.main()
