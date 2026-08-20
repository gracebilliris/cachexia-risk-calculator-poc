# Clinical logic test and traceability matrix

> **Scope of these tests:** software conformance only. Passing tests shows that
> the prototype implements the documented synthetic rules consistently. It
> does not establish that the rules are clinically correct, predictive,
> calibrated, validated, or suitable for patient care.

The executable decision table is
`tests/fixtures/clinical_logic_cases.v1.json`. Each case records its source,
review status, inputs, and expected tri-state outputs. The same cases are
executed independently against the Python and browser implementations.

The exhaustive generated matrix is available as:

- `data/clinical_logic_matrix.v1.json` for automated tests; and
- `excel/clinical_logic_review_matrix.v1.xlsx` for clinical review.

It contains all 324 combinations of nine weight-loss states, four BMI states,
three sarcopenia states, and three appetite states. Reviewer decisions and
comments can be recorded directly in the workbook.

The workbook is arranged for progressive review:

1. `START HERE` explains the rules, unknown handling, and review process.
2. `Key Scenarios` presents 12 representative examples in plain language.
3. `Review Decisions` captures decisions on each major clinical assumption.
4. `Full Logic Matrix` retains all 324 combinations for detailed filtering.
5. `Risk Assumptions` separates unvalidated score terms from classifications.

## Requirement traceability

| Requirement or assumption | Recorded source/status | Automated evidence |
|---|---|---|
| Every patient has an explicit prediction date | Confirmed project requirement | `test_core.py`, `test_generator.py` |
| Post-prediction measurements cannot affect predictors | Confirmed project requirement | Python and browser leakage-mutation tests |
| Three- and six-month horizons are separate | Confirmed project requirement | Python horizon-isolation tests and workbook formula tests |
| Exact horizon dates are included | Project operationalisation pending review | Calendar-boundary tests |
| BMI is weight kg / height m² | Confirmed project requirement | Python and browser arithmetic tests |
| Positive percentage means weight loss | Supplied clinical handoff formula | Python and browser arithmetic tests |
| Fearon primary branch uses loss >5% | Supplied clinical handoff | Shared decision-table cases and strict-boundary tests |
| Fearon BMI branch uses loss >2% and BMI <20 | Supplied clinical handoff | Shared decision-table cases, exact-2 and exact-BMI-20 tests |
| Fearon sarcopenia branch uses loss >2% with documented evidence | Subsequent project decision; clinical review pending | Shared yes/no/unknown decision-table cases |
| Sarcopenia is never inferred | Confirmed modelling constraint | Code path and workbook-reference tests |
| Unknown is not treated as no | Confirmed modelling constraint | Shared unknown sarcopenia/appetite cases and missing-data tests |
| Provisional early-risk pattern uses cachexia excluded, loss >1% and <=5%, appetite=yes | Project operationalisation pending clinical review | Shared lower/upper/appetite decision-table cases |
| The supplied ECOG distribution is retained with a declared 5% unknown allocation | Supplied proposal plus provisional missingness assumption | Configuration acceptance test |
| The supplied illustrative cancer and stage multipliers remain centralized | Simulation assumptions, not validated effects | Configuration acceptance test |
| Illustrative three-/six-month score arithmetic matches configured coefficients | Simulation assumptions, not a performance claim | Python and browser risk-arithmetic acceptance tests |
| Synthetic generation is reproducible | Technical requirement | Fixed-seed generator tests |
| Excel workbooks encode the same thresholds and input references | Technical requirement | OOXML/formula structure tests for both workbook editions |

## Versioned acceptance examples

The decision table includes representative cases for:

- loss just above 5%;
- exactly 5% with sarcopenia `yes`, `no`, and `unknown`;
- loss above 2% with BMI below 20;
- exactly 2%, which does not enter either conditional Fearon branch;
- exactly 1%, which does not enter the provisional early-risk interval;
- limited loss with appetite `yes`, `no`, and `unknown`; and
- a worked three-/six-month risk-score example using the configured
  colorectal, Stage III, ECOG 2, appetite, age, and weight-loss terms.

## What remains untested or unvalidated

- Clinical sensitivity, specificity, discrimination, calibration, utility,
  fairness, or transportability cannot be tested with rule-generated
  synthetic data.
- Clinical review has not approved the provisional early-risk rule,
  sarcopenia evidence definition, baseline sarcopenia carry-forward, or all
  simulation coefficients.
- Workbook tests inspect formulas and package structure in CI. Direct
  calculation behavior has also been exercised in desktop Microsoft Excel,
  but CI does not automate Microsoft Excel itself.
- A future real-data study would require ethics/governance approval,
  prespecified endpoints, an independent reference standard, and an
  appropriate validation design.
