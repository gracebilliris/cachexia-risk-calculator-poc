# Clinical logic test and traceability matrix

> **Software conformance only.** Passing tests shows consistent implementation
> of documented synthetic rules. It does not establish clinical correctness,
> performance, validation, or suitability for patient care.

The shared decision table is
`tests/fixtures/clinical_logic_cases.v1.json`. The exhaustive generated
artifacts are:

- `data/clinical_logic_matrix.v1.json`; and
- `excel/clinical_logic_review_matrix.v1.xlsx`.

The matrix retains all 324 combinations of nine weight-loss states, four BMI
states, three structural sarcopenia states, and three appetite states.
Sarcopenia combinations remain to verify that the baseline value does not
decide the disabled branch. For loss >2% and <=5% with BMI >=20, all three
values produce `unknown`, and provisional early-risk is also `unknown`.

The workbook review sequence is:

1. `START HERE`;
2. `Key Scenarios`;
3. `Review Decisions`;
4. `Full Logic Matrix`; and
5. `Category Assumptions`.

It preserves Times New Roman throughout and leaves non-table blank cells
unfilled/un-styled.

## Requirement traceability

| Requirement | Automated evidence |
|---|---|
| Predictor dates are on/before `prediction_date` | Python/browser leakage tests and workbook helper-formula tests |
| Current status is separate from future outcomes | Outcome provenance and schema tests |
| 3m and 6m are independent | Horizon mutation tests and separate workbook formulas |
| >5%, >2%, and BMI<20 are strict | Python/browser/matrix boundary cases |
| Disabled sarcopenia branch conservatively returns unknown when it could change the result | Python/browser/matrix/workbook formula tests |
| Baseline sarcopenia is never future evidence | Branch-toggle future-outcome regression test |
| Baseline appetite cannot alter future labels | No-follow-up mutation test |
| Follow-up appetite source is exact and required | Python validation rejection tests |
| Cancer subtype is required and matches cancer type | Python validation and schema tests |
| Dated follow-up appetite drives future candidate labels | Outcome and generator tests |
| Category uses only baseline predictors | Basis metadata and leakage tests |
| Unknown stage, ECOG, appetite, BMI, or loss withholds | Python/browser/workbook focused tests |
| Sex and subtype are unused | Python/browser mutation tests |
| Category is `low|moderate|high` | Python/browser/generated artifact tests |
| Category target outcome remains undefined | Config/schema/Python/browser/workbook tests |
| Future outcomes are not Fearon classifications and record actual intervals | Outcome/schema/generated artifact tests |
| Distribution summary includes baseline status impacts | Generated summary tests |
| Generated output exports no numeric model value | JSON/CSV/schema/workbook/browser contract tests |
| Pages does not publish workbooks | Workflow and HTML privacy test |
| Review artifacts are anonymous | Repository and OOXML content scan |
| Review workbook font/fill conventions persist | Openpyxl style tests |

## Versioned examples

The shared fixture covers:

- loss just above and exactly 5%;
- loss above and exactly 2%;
- BMI below and exactly 20;
- exactly 1%;
- appetite `yes|no|unknown`;
- sarcopenia `yes|no|unknown` with conservative unknown behavior for the
  disabled conditional branch; and
- a common 3-month/6-month ordinal category case for Python/browser parity.

## Not validated

Clinical sensitivity, specificity, discrimination, utility, fairness,
transportability, and real-world endpoint validity cannot be assessed with
rule-generated synthetic data. Eligibility, appetite evidence, sarcopenia
definition, provisional lower bound, endpoint framing, and continued display
of ordinal categories remain open clinical-review questions.
