# Implementation report

## Status

The reconciled stakeholder-review remediation is implemented across Python,
browser, schema/config, generated data, macro-free Excel, VBA Excel, clinical
review workbook, tests, and documentation.

The project remains synthetic, research-only, and not for clinical use.

## Implemented changes

- Separated retrospective baseline-derived criteria status from future
  synthetic threshold outcomes.
- Qualified the 3-month outcome as differing from Fearon 2011 in direction and
  window length.
- Qualified the 6-month outcome as not a Fearon classification despite its
  matching window length; it is a prospective research endpoint only, not a
  diagnosis.
- Added `fearon_classification=false` and actual `outcome_interval_days` to
  both future outcome objects and exports.
- Added dated synthetic follow-up appetite observations and prohibited
  baseline appetite carry-forward into future labels.
- Disabled the sarcopenia branch by default while retaining a tri-state
  future-use field. The >2% to <=5%, BMI >=20 branch now remains unknown, and
  baseline sarcopenia is never reused as future evidence.
- Added outcome basis/status/provenance and schema migration metadata.
- Replaced clinical-facing/generated numeric model outputs with separate
  3-month and 6-month `low|moderate|high` illustrative simulation categories.
- Added `target_outcome=not_defined_pending_clinical_review` to the canonical
  category contract and all category outputs; horizon differences remain
  simulation assumptions.
- Added explicit withholding for unknown stage, ECOG, appetite, BMI, or
  baseline weight change.
- Marked sex and lung subtype descriptive and unused in the category.
- Enforced exact follow-up appetite provenance and required cancer-subtype
  pairings.
- Added baseline cachexia and provisional early-risk distributions to the
  generated summary.
- Added neutral population wording: eligibility/inclusion criteria are not
  defined; cancer labels are synthetic adult solid-tumour stratifiers pending
  review.
- Preserved strict >5%, >2%, and BMI<20 boundaries and temporal leakage
  protections.
- Updated both workbook editions and the anonymous clinical review workbook.
- Preserved Times New Roman and non-table blank-cell no-fill conventions in the
  clinical review workbook.
- Kept workbook artifacts repository/local only; Pages publishes no workbook
  download.

## Provisional rule position

The early candidate rule remains explicitly provisional:

- >1% lower loss bound: editable, with no consensus basis;
- <=5% upper bound: consensus-aligned;
- appetite: binary POC simplification.

These and the remaining population, endpoint, sarcopenia, category-estimand,
and UX decisions remain pending in `CLINICAL_REVIEW_PACKAGE.md` and the review
workbook.

## Versioned artifacts

Config/schema version 1.1 introduces dated follow-up appetite evidence,
baseline/future separation, qualified outcome fields, provenance, and ordinal
category objects. The 120-record seed-`20260820` JSON, CSV, summary, browser
config, exhaustive 324-case matrix, and all three workbooks were regenerated
from canonical sources.

## Validation

- 75 Python tests passed.
- 17 Node browser-calculation tests passed.
- Python source/scripts compiled, JavaScript syntax checks passed, and all
  versioned JSON parsed.
- All three generated workbooks opened in desktop Microsoft Excel under their
  expected names without a repair report.
- Workbook formula/label tests confirmed separate 3-month/6-month category
  formulas, all five withholding conditions, no clinical-facing numeric model
  value, disabled sarcopenia logic, subtype handling, and safety wording.
- Review-workbook tests confirmed anonymity, Times New Roman, and unfilled
  non-table blank cells.
- Pages tests confirmed that no workbook is copied or linked for publication.

## Clinical basis

- Fearon K, et al. *Lancet Oncology*. 2011;12(5):489-495.
  <https://doi.org/10.1016/S1470-2045(10)70218-7>
- Muscaritoli M, et al. *Clinical Nutrition*. 2010;29(2):154-159.
  <https://doi.org/10.1016/j.clnu.2009.12.004>

No unsupported population, treatment, diagnostic, or exclusion claim has been
introduced.
