# Final implementation report

## Status

The synthetic-data proof of concept is implemented. It is not a validated
clinical prediction model and must not be used for diagnosis, prognosis,
treatment, patient care, or medical decisions.

## Completed work

- Versioned patient schema with explicit prediction date, units, enums,
  tri-state unknowns, separate pinned three-/six-month outcomes, and
  provenance.
- Strict baseline temporal filter and deterministic baseline/prior weight
  selection.
- BMI, positive percentage weight loss, exact interval, kg/month,
  percentage-points/month, and trajectory calculations with explicit
  non-calculable states.
- Inclusive calendar three-/six-month outcome boundaries and independent
  horizon evaluation.
- Traceable Fearon branches (>5% loss, >2% loss with BMI <20, or >2% loss
  with explicitly documented sarcopenia); sarcopenia is never inferred.
- Configurable provisional early-risk pattern (internal configuration name:
  Option B)
  (>1% and <=5% loss plus reduced appetite).
- Reproducible, seed-controlled longitudinal generator using the supplied
  workbook's proposed ranges where available.
- Central versioned simulation configuration and generated immutable browser
  configuration with automated parity coverage.
- Synthetic JSON and CSV cohort plus aggregate distribution summary.
- Static browser prototype with validation, unknown handling, separate risk
  outputs, factor explanations, classification traces, and prominent safety
  notice.
- Independent macro-free Excel prototype with validated input cells,
  transparent formulas, separate simulated horizons, synthetic cohort,
  assumptions, data dictionary, and structured clinical review sheets.
- Clinical review package and structured review-decision schema.

## Source material and assumptions

The workbook sheet `Prototype 1_agreed predictors` supplied proposed ranges
for age, sex, cancer categories, stage representation, sex-specific height,
weight, BMI, dated weight history, ECOG, appetite, and separate outcomes.
Those proposals are implemented as editable synthetic-testing inputs, not
confirmed clinical requirements.

All added distributions, probabilities, latent associations, future-weight
transitions, coefficients, multipliers, risk bands, and candidate
pre-cachexia thresholds are centralized in
`config/simulation_assumptions.v1.json`. The file labels every value as a
simulation assumption without calibration, discrimination, causal, treatment,
diagnostic, or prognostic meaning.

The configured tumour and stage values now match the supplied illustrative
multipliers. Their product is used only to create plausible synthetic
interaction; it is not a validated relative risk.

## Generated cohort

`data/synthetic_patients.v1.json` and `.csv` contain 120 patients generated
with seed `20260820` and config `1.0.0`. The sample contains 12/19/48/41
unknown/low/medium/high three-month simulated bands and 12/2/37/69
unknown/low/medium/high six-month bands. Unknown risk means the estimate was
withheld because BMI or baseline weight change was not calculable. The cohort
includes explicit labelled cases for unknown fields,
insufficient history, gain, stability, limited loss plus appetite, >5% loss,
BMI/loss lower boundaries, and 5% loss.

These counts demonstrate test coverage and sample variety only; they do not
estimate prevalence or performance.

## Validation results

The relocated repository's final run completed:

- 63 Python unit tests covering calculations, validation, missing values,
  duplicate/equal dates, irregular intervals, reproducibility, edge mix,
  browser-config parity, schema horizon pinning, post-baseline leakage,
  inclusive/exclusive boundaries, separate horizons, Fearon thresholds,
  sarcopenia unknowns, provisional pre-cachexia behavior, and Excel workbook
  sheets, formulas, validation, safety notice, config parity, VBA package
  structure, Form Control wiring, and version-controlled macro source.
- Repository and workbook privacy checks that prevent named reviewers from
  appearing in current text files or generated workbook contents.
- 11 direct Node browser-calculation tests covering BMI/loss, temporal leakage,
  missing history, classification boundaries, separate risk behavior, factor
  explanations, and calendar-month arithmetic.
- A versioned clinical-logic decision table executed against both Python and
  browser implementations, with source/status metadata and a worked
  three-/six-month score calculation.
- An exhaustive 324-case classification matrix and clinician review workbook
  covering every configured weight-loss, BMI, sarcopenia, and appetite state
  combination.
- Python bytecode compilation for `src/` and `scripts/`.
- JavaScript syntax checks for the generated config and prototype application.
- JSON parsing for all configuration, schema, data, summary, and review files.
- Deterministic regeneration of the 120-patient cohort.
- Reproducible generation of the macro-free
  `excel/cachexia_risk_prototype.v1.4.xlsx` and app-like
  `excel/cachexia_risk_mock_ui.v1.1.xlsm`.
- Direct Microsoft Excel opening of the VBA workbook without a repair dialog,
  execution of its high-risk sample macro and live formula outputs, and
  runtime confirmation that lung/non-lung selections update subtype values
  and visible guidance correctly.
- Public GitHub Pages deployment of the static JavaScript-parity prototype,
  with both Excel editions rebuilt and published as downloads by the
  deployment workflow.

An independent final review identified and prompted correction of stale UI
results after invalid input, duplicated browser assumptions, and insufficient
schema horizon constraints.

## Inputs unavailable or awaiting confirmation

The supplied materials do not contain recorded clinical approval or final
decisions for:

- exact population distributions beyond the workbook's proposed examples;
- confirmation or revision of the supplied illustrative cancer/stage
  multipliers and provisional ECOG/appetite relationships;
- future weight transition behavior and all risk coefficients/bands;
- confirmation or revision of provisional pre-cachexia Option B and its
  missing-appetite behavior;
- the baseline-to-horizon outcome measurement rule and inclusive boundaries;
- what constitutes documented sarcopenia evidence and whether dated
  horizon-specific muscle assessments must replace the provisional baseline
  carry-forward assumption; or
- whether the interface and explanations could be clinically misleading.

No unavailable input has been represented as approved. Clinical decisions
remain `pending` in `CLINICAL_REVIEW_PACKAGE.md` and should be
recorded using `review_decisions.schema.json` before any clinically informed
revision.

Statistical clinical hypothesis tests have not been performed because the POC
contains no real cohort, validated endpoint, prespecified inferential
hypothesis, or comparator. Current testing establishes software behavior only.
