#!/usr/bin/env python3
"""Generate exhaustive classification cases and a clinician review workbook."""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "simulation_assumptions.v1.json"
JSON_OUTPUT = ROOT / "data" / "clinical_logic_matrix.v1.json"
WORKBOOK_OUTPUT = ROOT / "excel" / "clinical_logic_review_matrix.v1.xlsx"

LOSS_STATES = (
    ("unavailable", None),
    ("gain_minus_2", -2.0),
    ("stable_0", 0.0),
    ("pre_lower_exact_1", 1.0),
    ("limited_1_5", 1.5),
    ("fearon_conditional_exact_2", 2.0),
    ("conditional_3", 3.0),
    ("primary_exact_5", 5.0),
    ("primary_over_5", 5.1),
)
BMI_STATES = (
    ("unavailable", None),
    ("below_20", 19.9),
    ("exact_20", 20.0),
    ("above_20", 25.0),
)
SARCOPENIA_STATES = ("yes", "no", "unknown")
APPETITE_STATES = ("yes", "no", "unknown")

NAVY = "17324D"
TEAL = "006D71"
PALE_TEAL = "DDEFEF"
PALE_ORANGE = "FFF1E9"
WHITE = "FFFFFF"
GREY = "E7ECEE"
THIN = Side(style="thin", color="B7C4C8")


def reference_cachexia(
    loss_percent: float | None,
    bmi: float | None,
    sarcopenia: str,
    definitions: dict[str, Any],
) -> tuple[str, str]:
    """Independent decision-table interpretation of the configured branches."""

    if loss_percent is None:
        return "unknown", "Weight loss is unavailable."
    if loss_percent > definitions["fearon_weight_loss_primary_exclusive"]:
        return "yes", "Weight loss is >5%."
    if loss_percent <= definitions["fearon_weight_loss_conditional_exclusive"]:
        return "no", "Loss is <=2%; both conditional branches require >2%."
    if bmi is not None and bmi < definitions["fearon_bmi_exclusive"]:
        return "yes", "Weight loss is >2% and BMI is <20 kg/m²."
    if (
        definitions["fearon_sarcopenia_branch_enabled"]
        and sarcopenia == "yes"
    ):
        return "yes", "Weight loss is >2% and sarcopenia is documented."
    if (
        bmi is not None
        and bmi >= definitions["fearon_bmi_exclusive"]
        and (
            not definitions["fearon_sarcopenia_branch_enabled"]
            or sarcopenia == "no"
        )
    ):
        return "no", "BMI and sarcopenia conditional branches are refuted."
    unavailable = []
    if bmi is None:
        unavailable.append("BMI")
    if (
        definitions["fearon_sarcopenia_branch_enabled"]
        and sarcopenia == "unknown"
    ):
        unavailable.append("sarcopenia")
    return "unknown", "Not evaluable because " + " and ".join(unavailable) + " are unknown."


def reference_early_risk(
    loss_percent: float | None,
    appetite: str,
    cachexia: str,
    definitions: dict[str, Any],
) -> tuple[str, str]:
    """Independent interpretation of the provisional early-risk rule."""

    if cachexia == "yes":
        return "no", "Cachexia criteria take precedence."
    if cachexia == "unknown":
        return "unknown", "Cachexia has not been excluded."
    if loss_percent is None:
        return "unknown", "Weight loss is unavailable."
    lower = definitions["precachexia_lower_weight_loss_percent_exclusive"]
    upper = definitions["precachexia_upper_weight_loss_percent_inclusive"]
    if not lower < loss_percent <= upper:
        return "no", f"Weight loss is outside ({lower}, {upper}]."
    if appetite == "yes":
        return "yes", "Limited loss and reduced appetite are both present."
    if appetite == "no":
        return "no", "Reduced appetite is explicitly absent."
    return "unknown", "Reduced appetite is unknown."


def generate_matrix(config: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = config["definitions"]
    cases = []
    combinations = itertools.product(
        LOSS_STATES,
        BMI_STATES,
        SARCOPENIA_STATES,
        APPETITE_STATES,
    )
    for index, ((loss_state, loss), (bmi_state, bmi), sarcopenia, appetite) in enumerate(
        combinations, 1
    ):
        cachexia, cachexia_reason = reference_cachexia(
            loss, bmi, sarcopenia, definitions
        )
        early_risk, early_risk_reason = reference_early_risk(
            loss, appetite, cachexia, definitions
        )
        boundary = (
            loss in {None, 1.0, 2.0, 5.0}
            or bmi in {None, 20.0}
            or sarcopenia == "unknown"
            or appetite == "unknown"
        )
        cases.append(
            {
                "case_id": f"LOGIC-{index:03d}",
                "weight_loss_state": loss_state,
                "weight_loss_percent": loss,
                "bmi_state": bmi_state,
                "bmi": bmi,
                "sarcopenia": sarcopenia,
                "reduced_appetite": appetite,
                "expected_cachexia": cachexia,
                "cachexia_rationale": cachexia_reason,
                "expected_early_risk": early_risk,
                "early_risk_rationale": early_risk_reason,
                "boundary_or_missing_case": boundary,
                "review_status": "pending",
            }
        )
    return cases


def write_json(config: dict[str, Any], cases: list[dict[str, Any]]) -> None:
    payload = {
        "metadata": {
            "version": "1.0.0",
            "purpose": "Exhaustive software-conformance and clinician-review matrix",
            "warning": (
                "Synthetic rule combinations only. Agreement does not establish "
                "clinical validity or approval."
            ),
            "clinical_approval": "pending clinical-reviewer and clinical-reviewer review",
            "combination_scope": (
                "9 weight-loss states x 4 BMI states x 3 sarcopenia states "
                "x 3 appetite states"
            ),
            "case_count": len(cases),
            "config_version": config["metadata"]["config_version"],
        },
        "states": {
            "weight_loss": [
                {"name": name, "value": value} for name, value in LOSS_STATES
            ],
            "bmi": [{"name": name, "value": value} for name, value in BMI_STATES],
            "sarcopenia": list(SARCOPENIA_STATES),
            "reduced_appetite": list(APPETITE_STATES),
        },
        "cases": cases,
    }
    JSON_OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def add_title(sheet, title: str, subtitle: str) -> None:
    sheet.merge_cells("A1:P1")
    sheet["A1"] = title
    sheet["A1"].font = Font(size=20, bold=True, color=WHITE)
    sheet["A1"].fill = PatternFill("solid", fgColor=NAVY)
    sheet["A1"].alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 32
    sheet.merge_cells("A2:P2")
    sheet["A2"] = subtitle
    sheet["A2"].font = Font(italic=True, color="44545B")
    sheet["A2"].alignment = Alignment(wrap_text=True, vertical="center")


def add_warning(sheet) -> None:
    sheet.merge_cells("A4:P5")
    sheet["A4"] = (
        "NOT FOR CLINICAL USE. These are synthetic rule combinations for logic "
        "review. Agreement confirms the intended implementation only; it does "
        "not establish clinical validity, accuracy, or approval."
    )
    sheet["A4"].font = Font(bold=True, color="7A2F12")
    sheet["A4"].fill = PatternFill("solid", fgColor=PALE_ORANGE)
    sheet["A4"].alignment = Alignment(wrap_text=True, vertical="center")
    sheet["A4"].border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def build_start_sheet(workbook: Workbook, cases: list[dict[str, Any]]) -> None:
    sheet = workbook.active
    sheet.title = "START HERE"
    add_title(
        sheet,
        "Clinical logic review matrix",
        "For clinical-reviewer and clinical-reviewer to confirm, reject, or question current prototype logic.",
    )
    add_warning(sheet)
    counts = Counter(
        (case["expected_cachexia"], case["expected_early_risk"]) for case in cases
    )
    instructions = [
        ("Scope", "324 combinations: 9 weight-loss states × 4 BMI states × 3 sarcopenia states × 3 appetite states."),
        ("How to review", "Filter Classification Matrix, then record agree/disagree/question, reviewer, and comments."),
        ("Cachexia", ">5% loss; or >2% with BMI <20; or >2% with documented sarcopenia."),
        ("Provisional early-risk", "Cachexia excluded, loss >1% and <=5%, and appetite=yes."),
        ("Unknown", "Unknown is never treated as no. Unavailable branches can keep classification unknown."),
        ("Sarcopenia", "yes=documented; no=assessed and absent; unknown=not assessed/documented. Never inferred."),
        ("Weight-loss assumption", "Matrix cases assume loss is involuntary for rule testing; the dataset has no separate involuntary-loss field."),
        ("Risk outputs", "Risk Terms lists simulation coefficients separately. No clinical performance claim is tested."),
        ("Clinical approval", "Pending. Completing this workbook records review; it does not itself validate the tool."),
    ]
    sheet["A8"], sheet["B8"] = "Topic", "Current interpretation"
    for row, (topic, text) in enumerate(instructions, 9):
        sheet.cell(row, 1, topic)
        sheet.cell(row, 2, text)
    sheet["A20"] = "Current output-count summary"
    sheet["A21"], sheet["B21"], sheet["C21"] = (
        "Cachexia",
        "Early-risk pattern",
        "Case count",
    )
    for row, ((cachexia, early_risk), count) in enumerate(sorted(counts.items()), 22):
        sheet.cell(row, 1, cachexia)
        sheet.cell(row, 2, early_risk)
        sheet.cell(row, 3, count)
    sheet.column_dimensions["A"].width = 28
    sheet.column_dimensions["B"].width = 100
    sheet.column_dimensions["C"].width = 16
    for row in range(8, sheet.max_row + 1):
        sheet.cell(row, 2).alignment = Alignment(wrap_text=True, vertical="top")


def build_matrix_sheet(workbook: Workbook, cases: list[dict[str, Any]]) -> None:
    sheet = workbook.create_sheet("Classification Matrix")
    add_title(
        sheet,
        "All classification combinations",
        "Expected outputs come from the documented reference decision table.",
    )
    add_warning(sheet)
    headers = [
        "Case ID",
        "Weight-loss state",
        "Loss %",
        "BMI state",
        "BMI",
        "Sarcopenia",
        "Reduced appetite",
        "Expected cachexia",
        "Cachexia rationale",
        "Expected early-risk pattern",
        "Early-risk rationale",
        "Boundary/missing?",
        "Rule status",
        "Reviewer decision",
        "Reviewer",
        "Comments / requested change",
    ]
    for column, header in enumerate(headers, 1):
        cell = sheet.cell(7, column, header)
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=TEAL)
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    for row, case in enumerate(cases, 8):
        values = [
            case["case_id"],
            case["weight_loss_state"],
            case["weight_loss_percent"],
            case["bmi_state"],
            case["bmi"],
            case["sarcopenia"],
            case["reduced_appetite"],
            case["expected_cachexia"],
            case["cachexia_rationale"],
            case["expected_early_risk"],
            case["early_risk_rationale"],
            "yes" if case["boundary_or_missing_case"] else "no",
            "provisional / review pending",
            "pending",
            None,
            None,
        ]
        for column, value in enumerate(values, 1):
            sheet.cell(row, column, value)
        for column in (14, 15, 16):
            sheet.cell(row, column).fill = PatternFill("solid", fgColor=PALE_TEAL)
    last_row = 7 + len(cases)
    decision = DataValidation(
        type="list",
        formula1='"pending,agree,disagree,question"',
        allow_blank=False,
    )
    decision.errorStyle = "stop"
    decision.error = "Choose pending, agree, disagree, or question."
    decision.showErrorMessage = True
    sheet.add_data_validation(decision)
    decision.add(f"N8:N{last_row}")
    sheet.auto_filter.ref = f"A7:P{last_row}"
    sheet.freeze_panes = "A8"
    widths = (14, 29, 12, 18, 12, 16, 18, 20, 55, 25, 55, 18, 25, 20, 20, 55)
    for column, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    for row in range(8, last_row + 1):
        for column in (9, 11, 16):
            sheet.cell(row, column).alignment = Alignment(
                wrap_text=True, vertical="top"
            )


def build_risk_terms_sheet(workbook: Workbook, config: dict[str, Any]) -> None:
    sheet = workbook.create_sheet("Risk Terms")
    add_title(
        sheet,
        "Illustrative risk-score terms",
        "Simulation assumptions only; these values are not validated clinical effects.",
    )
    add_warning(sheet)
    headers = ["Horizon", "Term", "Category", "Value", "Status"]
    for column, header in enumerate(headers, 1):
        sheet.cell(7, column, header)
    row = 8
    for horizon in ("three_month", "six_month"):
        terms = config["risk_outputs"][horizon]
        scalar_terms = {
            "intercept": terms["intercept"],
            "age_over_55": terms["age_over_55"],
            "baseline_weight_loss_per_percent": terms[
                "baseline_weight_loss_per_percent"
            ],
            "low_bmi_under_20": terms["low_bmi_under_20"],
            "cancer_type_multiplier": terms["cancer_type_multiplier"],
        }
        for term, value in scalar_terms.items():
            sheet.append(
                [
                    horizon,
                    term,
                    "all",
                    value,
                    "simulation assumption; not clinically validated",
                ]
            )
            row += 1
        for term in ("stage", "ecog", "appetite"):
            for category, value in terms[term].items():
                sheet.append(
                    [
                        horizon,
                        term,
                        category,
                        value,
                        "simulation assumption; not clinically validated",
                    ]
                )
                row += 1
    sheet.append([])
    sheet.append(
        ["Shared", "cancer risk multiplier", "Cancer type", "Value", "Status"]
    )
    for cancer_type, value in config["simulation_relationships"][
        "cancer_risk_multipliers"
    ].items():
        sheet.append(
            [
                "both",
                "cancer risk multiplier",
                cancer_type,
                value,
                "clinical-reviewer illustrative assumption; not a relative risk",
            ]
        )
    sheet.freeze_panes = "A8"
    sheet.auto_filter.ref = f"A7:E{sheet.max_row}"
    for column, width in enumerate((18, 38, 28, 16, 55), 1):
        sheet.column_dimensions[get_column_letter(column)].width = width


def build_decisions_sheet(workbook: Workbook) -> None:
    sheet = workbook.create_sheet("Review Decisions")
    add_title(
        sheet,
        "Structured clinical review decisions",
        "Record approved changes precisely; blank or pending does not mean approval.",
    )
    add_warning(sheet)
    headers = [
        "Decision ID",
        "Topic",
        "Current rule",
        "Decision",
        "Replacement rule / requested change",
        "Rationale",
        "Reviewer",
        "Date",
    ]
    for column, header in enumerate(headers, 1):
        sheet.cell(7, column, header)
    topics = [
        ("MATRIX-001", "Fearon primary boundary", "loss >5%"),
        ("MATRIX-002", "Fearon BMI branch", "loss >2% and BMI <20"),
        ("MATRIX-003", "Fearon sarcopenia branch", "loss >2% and documented sarcopenia"),
        ("MATRIX-004", "Unknown handling", "unknown branches do not become no"),
        ("MATRIX-005", "Provisional early-risk interval", "loss >1% and <=5%"),
        ("MATRIX-006", "Appetite requirement", "reduced appetite=yes"),
        ("MATRIX-007", "Sarcopenia evidence", "baseline explicit tri-state carried into synthetic horizons"),
        ("MATRIX-008", "Involuntary loss", "synthetic rule cases assume weight loss is involuntary"),
        ("MATRIX-009", "Risk terms", "illustrative configured coefficients and multipliers"),
    ]
    for row, values in enumerate(topics, 8):
        sheet.cell(row, 1, values[0])
        sheet.cell(row, 2, values[1])
        sheet.cell(row, 3, values[2])
        sheet.cell(row, 4, "pending")
    decision = DataValidation(
        type="list",
        formula1='"pending,approved,rejected,revision_requested"',
        allow_blank=False,
    )
    sheet.add_data_validation(decision)
    decision.add(f"D8:D{7 + len(topics)}")
    widths = (16, 30, 55, 22, 60, 50, 24, 18)
    for column, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    for row in range(8, 8 + len(topics)):
        for column in range(3, 7):
            sheet.cell(row, column).alignment = Alignment(
                wrap_text=True, vertical="top"
            )


def style_workbook(workbook: Workbook) -> None:
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None and cell.row >= 7:
                    cell.alignment = Alignment(
                        wrap_text=cell.alignment.wrap_text,
                        vertical=cell.alignment.vertical or "top",
                    )


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cases = generate_matrix(config)
    expected_count = (
        len(LOSS_STATES)
        * len(BMI_STATES)
        * len(SARCOPENIA_STATES)
        * len(APPETITE_STATES)
    )
    if len(cases) != expected_count:
        raise RuntimeError("Classification matrix is incomplete.")
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    WORKBOOK_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_json(config, cases)
    workbook = Workbook()
    build_start_sheet(workbook, cases)
    build_matrix_sheet(workbook, cases)
    build_risk_terms_sheet(workbook, config)
    build_decisions_sheet(workbook)
    style_workbook(workbook)
    workbook.active = 0
    workbook.save(WORKBOOK_OUTPUT)
    print(
        f"Built {JSON_OUTPUT.relative_to(ROOT)} and "
        f"{WORKBOOK_OUTPUT.relative_to(ROOT)} with {len(cases)} cases"
    )


if __name__ == "__main__":
    main()
