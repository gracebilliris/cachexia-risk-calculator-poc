# Clinical review package

**Review status: pending. No clinical approval is represented.**

This package concerns a synthetic, research-only POC. Clinical-facing outputs
are ordinal illustrative simulation categories, not clinical conclusions.
Workbook artifacts remain in `excel/` for repository/local review and are not
published on GitHub Pages.

The executable review cases are documented in
`CLINICAL_LOGIC_TEST_MATRIX.md`. The exhaustive workbook is
`../excel/clinical_logic_review_matrix.v1.xlsx`.

## Reconciled implementation position

- Fearon 2011 is retrospective over the past six months.
- Baseline-derived current criteria status is separated from future outcomes.
- The 3-month baseline-to-horizon label is a research-only threshold outcome
  that differs from Fearon in direction and window length.
- Although the 6-month label matches the six-month window length, it looks
  forward from baseline and is not a Fearon classification; it is a
  prospective research endpoint only, not a diagnosis.
- Future candidate labels use dated synthetic follow-up appetite observations;
  baseline appetite is not carried forward.
- Sarcopenia remains tri-state but future-use and pending definition. Baseline
  sarcopenia is never future evidence. When loss is >2% and <=5% and BMI is
  >=20, the disabled branch conservatively leaves status unknown.
- Clinical-facing model output is only `low|moderate|high`, or withheld with
  exact reasons.
- Target outcome is not defined pending clinical review. Horizon category
  differences are simulation assumptions only, and the categories remain
  illustrative.
- Sex and lung subtype are descriptive and unused in the category.

## Provisional pre-cachexia candidate

The current candidate rule is cachexia criteria excluded, loss >1% and <=5%,
and reduced appetite=`yes`.

- The >1% lower bound has no consensus basis and is an editable simulation
  parameter.
- The <=5% upper bound is consensus-aligned with Muscaritoli et al. (2010).
- Binary appetite is a POC simplification and does not implement the complete
  anorexia/metabolic-change concept.

## Decisions requested

| ID | Open question | Status |
|---|---|---|
| CLIN-001 | Confirm or revise synthetic predictor ranges/distributions | pending |
| CLIN-002 | Confirm stage/ECOG/appetite and cancer-stratifier simulation relationships | pending |
| CLIN-003 | Confirm, reject, or revise the provisional >1% to <=5% candidate interval and missing behavior | pending |
| CLIN-004 | Confirm retrospective baseline criteria implementation and strict >5%, >2%, BMI<20 boundaries | pending |
| CLIN-005 | Confirm 3-month/6-month measurement selection and qualified endpoint framing | pending |
| CLIN-006 | Define acceptable sarcopenia evidence before any future branch is enabled | pending |
| CLIN-007 | Define eligibility and inclusion criteria for the intended population | pending |
| CLIN-008 | Confirm dated follow-up appetite evidence and the binary appetite simplification | pending |
| CLIN-009 | Define the target outcome or estimand for the illustrative categories | pending |
| UX-001 | Identify wording or presentation that could imply clinical use | pending |

Additional workbook questions ask whether ordinal categories should remain,
whether synthetic tumour terms are acceptable, and what future real-data
design would be required. Absence of a recorded decision is not approval.

## Review focus

1. Baseline status versus future endpoint separation.
2. Strict threshold behavior at 1%, 2%, 5%, and BMI 20.
3. Withholding for unknown stage, ECOG, appetite, BMI, and baseline loss.
4. Dated follow-up appetite provenance and no baseline carry-forward.
5. Conservative unknown status for the disabled sarcopenia branch and no
   baseline sarcopenia carry-forward.
6. Neutral population notice and descriptive-only sex/subtype wording.
7. Ordinal category explanations and avoidance of numeric clinical-facing
   model output.
8. Definition of the target outcome or estimand before category interpretation.

## Citation basis

- Fearon K, et al. *Lancet Oncology*. 2011;12(5):489-495.
  <https://doi.org/10.1016/S1470-2045(10)70218-7>
- Muscaritoli M, et al. *Clinical Nutrition*. 2010;29(2):154-159.
  <https://doi.org/10.1016/j.clnu.2009.12.004>

Record structured decisions with `review_decisions.schema.json`, including
rationale, effective date, and exact requested changes.
