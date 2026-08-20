#!/usr/bin/env python3
"""Build the app-like, macro-enabled Excel prototype."""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

if sys.version_info < (3, 10):
    raise SystemExit(
        "The VBA workbook builder requires Python 3.10 or newer. "
        "Run it with python3.12 after installing the 'vba' optional dependencies."
    )

try:
    import xlsxwriter
    from pyopenvba import ExcelFile
except ImportError as error:
    raise SystemExit(
        "Install the VBA builder dependencies with "
        "python3.12 -m pip install -e '.[vba]'"
    ) from error


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "excel" / "cachexia_risk_mock_ui.v1.1.xlsm"
CONFIG_PATH = ROOT / "config" / "simulation_assumptions.v1.json"
VBA_SOURCE = ROOT / "vba" / "CachexiaUI.bas"
VBA_SHEET_SOURCE = ROOT / "vba" / "MockUISheet.cls"
VBA_WORKBOOK_SOURCE = ROOT / "vba" / "ThisWorkbook.cls"

INPUT_GUIDANCE = {
    9: "Required date. Records after this date cannot be predictors.",
    10: "Required whole number: 18 to 95 years.",
    11: "Valid: female, male or unknown.",
    12: "Required confirmed cancer type from the dropdown.",
    13: "Required for lung: SCLC, NSCLC or unknown.",
    14: "Valid: I, II, III, IV or unknown.",
    15: "Required: 140 to 200 cm.",
    16: "Valid: 0, 1, 2, 3, 4 or unknown.",
    17: "Valid: yes, no or unknown/not documented.",
    18: "Valid: yes, no or unknown. Stored but unused in v1.",
}

NAVY = "#17324D"
TEAL = "#006D71"
LIGHT_TEAL = "#DDEFEF"
BLUE_INPUT = "#D9EAF7"
PALE_ORANGE = "#FFF1E9"
ORANGE = "#C55A11"
WHITE = "#FFFFFF"
GREY = "#E7ECEE"
DARK_GREY = "#44545B"
RED = "#C00000"
GREEN = "#548235"


def create_vba_project(destination: Path) -> None:
    source = VBA_SOURCE.read_text(encoding="utf-8").replace("\n", "\r\n")
    sheet_source = VBA_SHEET_SOURCE.read_text(encoding="utf-8").replace(
        "\n", "\r\n"
    )
    workbook_source = VBA_WORKBOOK_SOURCE.read_text(encoding="utf-8").replace(
        "\n", "\r\n"
    )
    with tempfile.TemporaryDirectory() as temporary_directory:
        template = Path(temporary_directory) / "macro_template.xlsm"
        with ExcelFile.create_new(template) as workbook:
            project = workbook.vba_project()
            project.rename_module("Module1", "CachexiaUI")
            workbook.set_module("CachexiaUI", source)
            workbook.set_module("Sheet1", sheet_source)
            workbook.set_module("ThisWorkbook", workbook_source)
            workbook.save()
        with ZipFile(template) as archive:
            destination.write_bytes(archive.read("xl/vbaProject.bin"))


def add_list_validation(sheet, cell: str, values: list[str]) -> None:
    sheet.data_validation(
        cell,
        {
            "validate": "list",
            "source": values,
            "input_title": "Select a value",
            "input_message": "Unknown is distinct from no.",
            "error_title": "Invalid category",
            "error_message": "Choose a value from the dropdown.",
            "error_type": "stop",
        },
    )


def write_safety_notice(sheet, formats: dict) -> None:
    sheet.merge_range(
        "A3:L5",
        "NOT FOR CLINICAL USE. All patients and outputs are synthetic. "
        "Risk relationships are simulation assumptions, not clinically "
        "validated effects. Do not use for diagnosis, prognosis, treatment, "
        "patient care, or medical decisions.",
        formats["warning"],
    )


def build_mock_ui(workbook, config: dict, formats: dict) -> None:
    sheet = workbook.add_worksheet("Mock UI")
    sheet.set_vba_name("Sheet1")
    sheet.activate()
    sheet.hide_gridlines(2)
    sheet.set_tab_color(TEAL)
    sheet.freeze_panes(7, 0)
    sheet.set_column("A:A", 3)
    sheet.set_column("B:B", 27)
    sheet.set_column("C:C", 20)
    sheet.set_column("D:F", 10)
    sheet.set_column("G:G", 25)
    sheet.set_column("H:I", 16)
    sheet.set_column("J:J", 3)
    sheet.set_column("K:L", 17)
    sheet.set_column("M:N", None, None, {"hidden": True})

    sheet.merge_range("A1:L1", "Synthetic cachexia risk mock UI", formats["title"])
    sheet.merge_range(
        "A2:L2",
        "Enter a synthetic profile, use a sample button, and review separate "
        "three- and six-month illustrative outputs.",
        formats["subtitle"],
    )
    write_safety_notice(sheet, formats)

    sheet.merge_range("A7:C7", "1  Synthetic patient inputs", formats["section"])
    input_rows = [
        (9, "Prediction date", datetime(2026, 1, 31), "date"),
        (10, "Age (years)", 65, "integer"),
        (11, "Sex", "female", "list"),
        (12, "Cancer type", "lung", "list"),
        (13, "Cancer subtype", "NSCLC", "text"),
        (14, "Cancer stage", "III", "list"),
        (15, "Height (cm)", 170, "decimal"),
        (16, "Baseline ECOG", "2", "list"),
        (17, "Reduced appetite", "no", "list"),
        (18, "Sarcopenia (stored; unused in v1)", "unknown", "list"),
    ]
    for row, label, value, value_type in input_rows:
        sheet.write(row - 1, 1, label, formats["label"])
        if value_type == "date":
            sheet.write_datetime(row - 1, 2, value, formats["input_date"])
        else:
            sheet.write(row - 1, 2, value, formats["input"])
        sheet.merge_range(
            row - 1,
            3,
            row - 1,
            5,
            INPUT_GUIDANCE[row],
            formats["guidance"],
        )
        sheet.set_row(row - 1, 30)

    add_list_validation(sheet, "C11", ["female", "male", "unknown"])
    add_list_validation(
        sheet, "C12", list(config["cohort"]["cancer_type_probabilities"])
    )
    add_list_validation(sheet, "C14", ["I", "II", "III", "IV", "unknown"])
    add_list_validation(sheet, "C16", ["0", "1", "2", "3", "4", "unknown"])
    add_list_validation(sheet, "C17", ["yes", "no", "unknown"])
    add_list_validation(sheet, "C18", ["yes", "no", "unknown"])
    sheet.data_validation(
        "C13",
        {
            "validate": "list",
            "source": '=INDIRECT(IF($C$12="lung","LungSubtypeValues","NonLungSubtypeValues"))',
            "input_title": "Lung subtype",
            "input_message": "SCLC, NSCLC or unknown for lung; otherwise not applicable.",
            "error_title": "Invalid subtype",
            "error_message": "Choose a value permitted for the selected cancer type.",
            "error_type": "stop",
        },
    )
    sheet.data_validation(
        "C9",
        {
            "validate": "date",
            "criteria": "between",
            "minimum": datetime(2000, 1, 1),
            "maximum": datetime(2100, 12, 31),
            "error_title": "Invalid date",
            "error_message": "Enter a valid prediction date.",
            "error_type": "stop",
        },
    )
    sheet.data_validation(
        "C10",
        {
            "validate": "integer",
            "criteria": "between",
            "minimum": config["cohort"]["age"]["minimum"],
            "maximum": config["cohort"]["age"]["maximum"],
            "error_title": "Invalid age",
            "error_message": "Enter an age from 18 to 95.",
            "error_type": "stop",
        },
    )
    sheet.data_validation(
        "C15",
        {
            "validate": "decimal",
            "criteria": "between",
            "minimum": 140,
            "maximum": 200,
            "error_title": "Invalid height",
            "error_message": "Enter a height from 140 to 200 cm.",
            "error_type": "stop",
        },
    )

    sheet.merge_range("A21:C21", "2  Dated weight history", formats["section"])
    sheet.write("B22", "Measurement date", formats["table_header"])
    sheet.write("C22", "Weight (kg)", formats["table_header"])
    default_weights = [
        (datetime(2025, 7, 31), 80),
        (datetime(2026, 1, 31), 76),
    ]
    weight_min = config["cohort"]["historical_weight_kg"]["minimum"]
    weight_max = config["cohort"]["historical_weight_kg"]["maximum"]
    for index, row in enumerate(range(24, 34)):
        if index < len(default_weights):
            weight_date, weight = default_weights[index]
            sheet.write_datetime(row - 1, 1, weight_date, formats["input_date"])
            sheet.write_number(row - 1, 2, weight, formats["input_weight"])
        else:
            sheet.write_blank(row - 1, 1, None, formats["input_date"])
            sheet.write_blank(row - 1, 2, None, formats["input_weight"])
        sheet.write_formula(
            row - 1,
            12,
            f'=IF(AND(ISNUMBER(B{row}),ISNUMBER(C{row}),B{row}<=$C$9,'
            f"C{row}>={weight_min},C{row}<={weight_max}),B{row},0)",
        )
        sheet.write_formula(
            row - 1,
            13,
            f'=IF(AND(ISNUMBER(B{row}),ISNUMBER(C{row}),Engine!$B$8<>\"\",'
            f"B{row}<Engine!$B$8,B{row}>=EDATE(Engine!$B$8,-6),"
            f"C{row}>={weight_min},C{row}<={weight_max}),"
            f"B{row},DATE(9999,12,31))",
        )

    sheet.data_validation(
        "B24:B33",
        {
            "validate": "date",
            "criteria": "between",
            "minimum": datetime(2000, 1, 1),
            "maximum": datetime(2100, 12, 31),
            "ignore_blank": True,
            "error_title": "Invalid date",
            "error_message": "Enter a valid date or clear the row.",
            "error_type": "stop",
        },
    )
    sheet.data_validation(
        "C24:C33",
        {
            "validate": "decimal",
            "criteria": "between",
            "minimum": weight_min,
            "maximum": weight_max,
            "ignore_blank": True,
            "error_title": "Invalid weight",
            "error_message": f"Enter a weight from {weight_min} to {weight_max} kg.",
            "error_type": "stop",
        },
    )

    sheet.merge_range("G7:L7", "3  Automatic synthetic outputs", formats["section"])
    output_rows = [
        (9, "Baseline/current weight", "=Engine!B9", formats["result_kg"]),
        (10, "BMI", "=Engine!B12", formats["result_number"]),
        (11, "Weight loss", "=Engine!B13/100", formats["result_percent"]),
        (12, "Interval", "=Engine!B14", formats["result_days"]),
        (13, "Weight-loss rate", "=Engine!B15", formats["result_rate"]),
        (14, "Trajectory", "=Engine!B17", formats["result_text"]),
        (16, "Implemented cachexia criteria met?", "=Engine!B19", formats["result_text"]),
        (17, "Provisional early-risk pattern met?", "=Engine!B20", formats["result_text"]),
    ]
    for row, label, formula, result_format in output_rows:
        sheet.write(row - 1, 6, label, formats["label"])
        sheet.merge_range(row - 1, 7, row - 1, 8, "", result_format)
        sheet.write_formula(row - 1, 7, formula, result_format)

    sheet.merge_range("G20:I20", "3-month illustrative output", formats["card_title"])
    sheet.merge_range("K20:L20", "6-month illustrative output", formats["card_title"])
    sheet.merge_range("G21:I22", "", formats["risk_card"])
    sheet.write_formula("G21", "=Engine!B25", formats["risk_card"])
    sheet.merge_range("K21:L22", "", formats["risk_card"])
    sheet.write_formula("K21", "=Engine!D25", formats["risk_card"])
    sheet.write("G23", "Risk band", formats["label"])
    sheet.merge_range("H23:I23", "", formats["result_text"])
    sheet.write_formula("H23", "=Engine!B26", formats["result_text"])
    sheet.write("K23", "Risk band", formats["label"])
    sheet.write_formula("L23", "=Engine!D26", formats["result_text"])
    sheet.merge_range("G25:L27", "", formats["explanation"])
    sheet.write_formula(
        "G25",
        '="3m: "&Engine!B27&CHAR(10)&"6m: "&Engine!D27',
        formats["explanation"],
    )

    sheet.merge_range(
        "G29:L32",
        "Rules shown in plain language\n"
        "Implemented cachexia criteria: >5% weight loss, or >2% weight loss "
        "with BMI <20 kg/m². The sarcopenia branch is not evaluated.\n"
        "Provisional early-risk pattern: cachexia criteria not met, >1% and "
        "<=5% weight loss, and reduced appetite=yes. This project proposal "
        "requires clinical-reviewer and clinical-reviewer's review.",
        formats["definition"],
    )

    button_options = [
        ("B36", "Calculate / validate", "CalculateRisk", 170),
        ("D36", "Reset form", "ResetForm", 120),
        ("B39", "Load low-risk example", "LoadLowRiskExample", 170),
        ("D39", "Load high-risk example", "LoadHighRiskExample", 170),
        ("G36", "Open clinical review", "OpenClinicalReview", 170),
    ]
    for cell, caption, macro, width in button_options:
        sheet.insert_button(
            cell,
            {
                "macro": macro,
                "caption": caption,
                "width": width,
                "height": 30,
            },
        )
    sheet.merge_range(
        "G39:L41",
        "Buttons require macros to be enabled. Inputs, dropdowns, formulas, "
        "and live outputs still work when macros are disabled.",
        formats["macro_note"],
    )


def build_engine(workbook, config: dict, formats: dict) -> None:
    sheet = workbook.add_worksheet("Engine")
    sheet.hide()
    labels = {
        8: "Baseline weight date",
        9: "Baseline/current weight (kg)",
        10: "Prior comparison date",
        11: "Prior comparison weight (kg)",
        12: "BMI (kg/m²)",
        13: "Percentage weight loss (+ = loss)",
        14: "Interval (days)",
        15: "Weight-loss rate (kg/month)",
        16: "Rate (percentage points/month)",
        17: "Trajectory",
        19: "Implemented cachexia criteria met?",
        20: "Provisional early-risk pattern met?",
    }
    for row, label in labels.items():
        sheet.write(row - 1, 0, label)

    dates = "'Mock UI'!$B$24:$B$33"
    weights = "'Mock UI'!$C$24:$C$33"
    baseline_candidates = "'Mock UI'!$M$24:$M$33"
    prior_candidates = "'Mock UI'!$N$24:$N$33"
    weight_min = config["cohort"]["historical_weight_kg"]["minimum"]
    weight_max = config["cohort"]["historical_weight_kg"]["maximum"]
    formulas = {
        "B8": f'=IF(MAX({baseline_candidates})=0,"",MAX({baseline_candidates}))',
        "B9": (
            f'=IF(B8="","",IF(COUNTIFS({dates},B8,{weights},">={weight_min}",'
            f'{weights},"<={weight_max}")<>1,"",SUMIFS({weights},{dates},B8,'
            f'{weights},">={weight_min}",{weights},"<={weight_max}")))'
        ),
        "B10": (
            f'=IF(OR(B8="",MIN({prior_candidates})=DATE(9999,12,31)),"",'
            f"MIN({prior_candidates}))"
        ),
        "B11": (
            f'=IF(B10="","",IF(COUNTIFS({dates},B10,{weights},">={weight_min}",'
            f'{weights},"<={weight_max}")<>1,"",SUMIFS({weights},{dates},B10,'
            f'{weights},">={weight_min}",{weights},"<={weight_max}")))'
        ),
        "B12": '=IF(OR(B9="",\'Mock UI\'!C15=""),"",B9/(\'Mock UI\'!C15/100)^2)',
        "B13": '=IF(OR(B9="",B11=""),"",((B11-B9)/B11)*100)',
        "B14": '=IF(OR(B8="",B10=""),"",B8-B10)',
        "B15": '=IF(OR(B9="",B11="",B14<=0),"",(B11-B9)/(B14/Assumptions!$B$8))',
        "B16": '=IF(OR(B13="",B14<=0),"",B13/(B14/Assumptions!$B$8))',
        "B17": '=IF(B13="","unknown",IF(B13>Assumptions!$B$9,"loss",IF(B13<-Assumptions!$B$9,"gain","stable")))',
        "B19": (
            '=IF(B13="","unknown",IF(B13>Assumptions!$B$10,"yes",'
            'IF(B13<=Assumptions!$B$11,"no",IF(B12="","unknown",'
            'IF(B12<Assumptions!$B$12,"yes","no")))))'
        ),
        "B20": (
            '=IF(B19="unknown","unknown",IF(B19="yes","no",'
            'IF(OR(B13<=Assumptions!$B$13,B13>Assumptions!$B$14),"no",'
            'IF(\'Mock UI\'!C17="yes","yes",IF(\'Mock UI\'!C17="no","no","unknown")))))'
        ),
    }
    for cell, formula in formulas.items():
        sheet.write_formula(cell, formula)

    sheet.write("A23", "Simulated horizon")
    sheet.write("B23", "3 months")
    sheet.write("D23", "6 months")
    common3 = (
        "Assumptions!$B$20+IF('Mock UI'!C10>Assumptions!$B$15,Assumptions!$B$21,0)"
        "+VLOOKUP('Mock UI'!C14,Assumptions!$H$8:$J$12,2,FALSE)"
        "+VLOOKUP('Mock UI'!C16&\"\",Assumptions!$L$8:$N$13,2,FALSE)"
        "+VLOOKUP('Mock UI'!C17,Assumptions!$P$8:$R$10,2,FALSE)"
        "+MAX(0,N(B13))*Assumptions!$B$22"
        "+IF(AND(B12<>\"\",B12<Assumptions!$B$12),Assumptions!$B$23,0)"
        "+(VLOOKUP('Mock UI'!C12,Assumptions!$E$8:$F$17,2,FALSE)-1)*Assumptions!$B$24"
    )
    common6 = (
        "Assumptions!$B$25+IF('Mock UI'!C10>Assumptions!$B$15,Assumptions!$B$26,0)"
        "+VLOOKUP('Mock UI'!C14,Assumptions!$H$8:$J$12,3,FALSE)"
        "+VLOOKUP('Mock UI'!C16&\"\",Assumptions!$L$8:$N$13,3,FALSE)"
        "+VLOOKUP('Mock UI'!C17,Assumptions!$P$8:$R$10,3,FALSE)"
        "+MAX(0,N(B13))*Assumptions!$B$27"
        "+IF(AND(B12<>\"\",B12<Assumptions!$B$12),Assumptions!$B$28,0)"
        "+(VLOOKUP('Mock UI'!C12,Assumptions!$E$8:$F$17,2,FALSE)-1)*Assumptions!$B$29"
    )
    sheet.write_formula("B24", f'=IF(OR(B12="",B13=""),"",{common3})')
    sheet.write_formula("D24", f'=IF(OR(B12="",B13=""),"",{common6})')
    sheet.write_formula("B25", '=IF(B24="","",1/(1+EXP(-B24)))')
    sheet.write_formula("D25", '=IF(D24="","",1/(1+EXP(-D24)))')
    sheet.write_formula(
        "B26",
        '=IF(B25="","unknown",IF(B25<Assumptions!$B$16,"low",'
        'IF(B25>=Assumptions!$B$17,"high","medium")))',
    )
    sheet.write_formula(
        "D26",
        '=IF(D25="","unknown",IF(D25<Assumptions!$B$16,"low",'
        'IF(D25>=Assumptions!$B$17,"high","medium")))',
    )
    factor_formula = (
        'TRIM(IF(\'Mock UI\'!C10>Assumptions!$B$15,"age >55; ","")&'
        'IF(B13>0,"baseline loss "&TEXT(B13,"0.0")&"%; ","")&'
        'IF(AND(B12<>"",B12<Assumptions!$B$12),"BMI <20; ","")&'
        '"stage "&\'Mock UI\'!C14&"; ECOG "&\'Mock UI\'!C16&'
        '"; appetite="&\'Mock UI\'!C17&"; "&\'Mock UI\'!C12)'
    )
    withheld = (
        '=IF(OR(B12="",B13=""),'
        '"Estimate withheld: BMI and baseline weight change are required.",'
        f"{factor_formula})"
    )
    sheet.write_formula("B27", withheld)
    sheet.write_formula("D27", withheld)


def build_assumptions(workbook, config: dict) -> None:
    sheet = workbook.add_worksheet("Assumptions")
    sheet.hide()
    definitions = config["definitions"]
    scalar_rows = [
        ("DaysPerMonth", definitions["days_per_month"]),
        ("TrajectoryEpsilon", definitions["trajectory_epsilon_percent"]),
        ("FearonPrimary", definitions["fearon_weight_loss_primary_exclusive"]),
        ("FearonConditional", definitions["fearon_weight_loss_conditional_exclusive"]),
        ("FearonBMI", definitions["fearon_bmi_exclusive"]),
        ("PreLower", definitions["precachexia_lower_weight_loss_percent_exclusive"]),
        ("PreUpper", definitions["precachexia_upper_weight_loss_percent_inclusive"]),
        ("AgeThreshold", config["risk_outputs"]["age_threshold_exclusive"]),
        ("BandLow", config["risk_outputs"]["band_thresholds"]["low_upper_exclusive"]),
        ("BandHigh", config["risk_outputs"]["band_thresholds"]["high_lower_inclusive"]),
        ("WeightMin", config["cohort"]["historical_weight_kg"]["minimum"]),
        ("WeightMax", config["cohort"]["historical_weight_kg"]["maximum"]),
    ]
    for horizon, prefix in (("three_month", "Risk3"), ("six_month", "Risk6")):
        values = config["risk_outputs"][horizon]
        scalar_rows.extend(
            [
                (f"{prefix}Intercept", values["intercept"]),
                (f"{prefix}Age", values["age_over_55"]),
                (f"{prefix}Loss", values["baseline_weight_loss_per_percent"]),
                (f"{prefix}BMI", values["low_bmi_under_20"]),
                (f"{prefix}Cancer", values["cancer_type_multiplier"]),
            ]
        )
    for offset, (key, value) in enumerate(scalar_rows, 8):
        sheet.write(offset - 1, 0, key)
        sheet.write(offset - 1, 1, value)

    cancer = config["simulation_relationships"]["cancer_risk_multipliers"]
    for row, (key, value) in enumerate(cancer.items(), 8):
        sheet.write(row - 1, 4, key)
        sheet.write(row - 1, 5, value)
    stages = list(config["risk_outputs"]["three_month"]["stage"])
    for row, key in enumerate(stages, 8):
        sheet.write(row - 1, 7, key)
        sheet.write(row - 1, 8, config["risk_outputs"]["three_month"]["stage"][key])
        sheet.write(row - 1, 9, config["risk_outputs"]["six_month"]["stage"][key])
    ecogs = list(config["risk_outputs"]["three_month"]["ecog"])
    for row, key in enumerate(ecogs, 8):
        sheet.write(row - 1, 11, key)
        sheet.write(row - 1, 12, config["risk_outputs"]["three_month"]["ecog"][key])
        sheet.write(row - 1, 13, config["risk_outputs"]["six_month"]["ecog"][key])
    appetites = list(config["risk_outputs"]["three_month"]["appetite"])
    for row, key in enumerate(appetites, 8):
        sheet.write(row - 1, 15, key)
        sheet.write(row - 1, 16, config["risk_outputs"]["three_month"]["appetite"][key])
        sheet.write(row - 1, 17, config["risk_outputs"]["six_month"]["appetite"][key])
    for row, subtype in enumerate(("SCLC", "NSCLC", "unknown"), 8):
        sheet.write(row - 1, 19, subtype)
    sheet.write("U8", "not applicable")


def build_clinical_review(workbook, formats: dict) -> None:
    sheet = workbook.add_worksheet("Clinical Review")
    sheet.hide_gridlines(2)
    sheet.set_column("A:A", 14)
    sheet.set_column("B:B", 58)
    sheet.set_column("C:C", 24)
    sheet.set_column("D:D", 22)
    sheet.set_column("E:F", 40)
    sheet.set_column("G:G", 18)
    sheet.merge_range("A1:G1", "clinical-reviewer and clinical-reviewer review decisions", formats["title"])
    sheet.merge_range(
        "A2:G2",
        "No approval has been received. Record decisions explicitly; blank is not approval.",
        formats["subtitle"],
    )
    sheet.merge_range(
        "A4:G5",
        "NOT FOR CLINICAL USE. Review of this workbook does not constitute "
        "clinical validation or approval.",
        formats["warning"],
    )
    headers = ["ID", "Question", "Owner", "Status", "Decision", "Rationale", "Effective date"]
    for column, header in enumerate(headers):
        sheet.write(6, column, header, formats["table_header"])
    questions = [
        ("CLIN-001", "Confirm/revise predictor ranges and distributions"),
        ("CLIN-002", "Confirm stage/ECOG/appetite simulation relationships"),
        ("CLIN-003", "Approve/reject/revise provisional pre-cachexia rule"),
        ("CLIN-004", "Confirm Fearon implementation and unknown behavior"),
        ("CLIN-005", "Confirm outcome selection and inclusive boundaries"),
        ("CLIN-006", "Confirm sarcopenia representation"),
        ("UX-001", "Identify clinically misleading wording or presentation"),
    ]
    for row, (identifier, question) in enumerate(questions, 7):
        sheet.write(row, 0, identifier)
        sheet.write(row, 1, question)
        sheet.write(row, 2, "clinical-reviewer; clinical-reviewer")
        sheet.write(row, 3, "pending", formats["review_input"])
        sheet.write_blank(row, 4, None, formats["review_input"])
        sheet.write_blank(row, 5, None, formats["review_input"])
        sheet.write_blank(row, 6, None, formats["review_input"])
    sheet.data_validation(
        f"D8:D{7 + len(questions)}",
        {
            "validate": "list",
            "source": ["pending", "approved", "rejected", "revision_requested"],
        },
    )
    sheet.insert_button(
        "A18",
        {
            "macro": "OpenMockUI",
            "caption": "Return to mock UI",
            "width": 150,
            "height": 30,
        },
    )


def make_formats(workbook) -> dict:
    border = 1
    return {
        "title": workbook.add_format(
            {"bold": True, "font_size": 20, "font_color": WHITE, "bg_color": NAVY, "align": "left", "valign": "vcenter"}
        ),
        "subtitle": workbook.add_format(
            {"italic": True, "font_color": DARK_GREY, "text_wrap": True, "valign": "vcenter"}
        ),
        "warning": workbook.add_format(
            {"bold": True, "font_color": "#7A2F12", "bg_color": PALE_ORANGE, "border": border, "text_wrap": True, "valign": "vcenter"}
        ),
        "section": workbook.add_format(
            {"bold": True, "font_size": 13, "font_color": WHITE, "bg_color": TEAL, "align": "left", "valign": "vcenter"}
        ),
        "label": workbook.add_format({"bold": True, "font_color": NAVY, "valign": "vcenter"}),
        "input": workbook.add_format({"bg_color": BLUE_INPUT, "border": border, "valign": "vcenter"}),
        "input_date": workbook.add_format({"bg_color": BLUE_INPUT, "border": border, "num_format": "yyyy-mm-dd", "valign": "vcenter"}),
        "input_weight": workbook.add_format({"bg_color": BLUE_INPUT, "border": border, "num_format": '0.00 "kg"', "valign": "vcenter"}),
        "table_header": workbook.add_format({"bold": True, "font_color": WHITE, "bg_color": TEAL, "border": border, "align": "center"}),
        "result_kg": workbook.add_format({"bg_color": LIGHT_TEAL, "border": border, "bold": True, "num_format": '0.00 "kg"', "align": "center"}),
        "result_number": workbook.add_format({"bg_color": LIGHT_TEAL, "border": border, "bold": True, "num_format": "0.00", "align": "center"}),
        "result_percent": workbook.add_format({"bg_color": LIGHT_TEAL, "border": border, "bold": True, "num_format": "0.00%", "align": "center"}),
        "result_days": workbook.add_format({"bg_color": LIGHT_TEAL, "border": border, "bold": True, "num_format": '0 "days"', "align": "center"}),
        "result_rate": workbook.add_format({"bg_color": LIGHT_TEAL, "border": border, "bold": True, "num_format": '0.00 "kg/month"', "align": "center"}),
        "result_text": workbook.add_format({"bg_color": LIGHT_TEAL, "border": border, "bold": True, "align": "center", "valign": "vcenter"}),
        "card_title": workbook.add_format({"bold": True, "font_color": WHITE, "bg_color": NAVY, "align": "center"}),
        "risk_card": workbook.add_format({"bold": True, "font_size": 20, "font_color": TEAL, "bg_color": LIGHT_TEAL, "border": border, "num_format": "0.0%", "align": "center", "valign": "vcenter"}),
        "explanation": workbook.add_format({"bg_color": GREY, "border": border, "text_wrap": True, "valign": "top"}),
        "definition": workbook.add_format({"bg_color": PALE_ORANGE, "border": border, "text_wrap": True, "valign": "top"}),
        "macro_note": workbook.add_format({"italic": True, "font_color": DARK_GREY, "bg_color": GREY, "border": border, "text_wrap": True, "valign": "vcenter"}),
        "review_input": workbook.add_format({"bg_color": BLUE_INPUT, "border": border, "text_wrap": True, "valign": "top"}),
        "guidance": workbook.add_format(
            {
                "font_size": 9,
                "font_color": DARK_GREY,
                "bg_color": GREY,
                "border": border,
                "text_wrap": True,
                "valign": "vcenter",
            }
        ),
    }


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary_directory:
        vba_project = Path(temporary_directory) / "vbaProject.bin"
        create_vba_project(vba_project)
        workbook = xlsxwriter.Workbook(OUTPUT)
        workbook.add_vba_project(vba_project)
        workbook.set_vba_name("ThisWorkbook")
        workbook.define_name("LungSubtypeValues", "=Assumptions!$T$8:$T$10")
        workbook.define_name("NonLungSubtypeValues", "=Assumptions!$U$8:$U$8")
        workbook.set_properties(
            {
                "title": "Synthetic cachexia risk mock UI",
                "subject": "Research-only synthetic proof of concept",
                "comments": "Not clinically validated. Do not use for medical decisions.",
            }
        )
        workbook.set_calc_mode("auto")
        formats = make_formats(workbook)
        build_mock_ui(workbook, config, formats)
        build_engine(workbook, config, formats)
        build_assumptions(workbook, config)
        build_clinical_review(workbook, formats)
        workbook.close()
    print(f"Built {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
