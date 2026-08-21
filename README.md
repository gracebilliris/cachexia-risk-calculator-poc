# Synthetic cachexia simulation proof of concept

> **Research-only and not for clinical use.** All records and outputs are
> synthetic. Every distribution, coefficient, multiplier, threshold, and
> relationship is an editable simulation assumption. Do not use this project
> for diagnosis, prognosis, treatment, patient care, or medical decisions.

This dependency-light Python/static-web POC demonstrates:

- baseline-derived current cachexia criteria status;
- a provisional pre-cachexia candidate rule;
- qualified 3-month and 6-month synthetic follow-up outcomes; and
- separate 3-month and 6-month ordinal **illustrative simulation categories**
  (`low`, `moderate`, or `high`) based on baseline predictors only.

Eligibility and inclusion criteria are not yet defined. The cancer-type labels
are synthetic stratifiers for an adult solid-tumour POC pending clinical
review. They do not establish an agreed population definition.

**Live synthetic demonstrator:** <https://gracebilliris.github.io/cachexia-risk-calculator-poc/>

## Safe output contract

Clinical-facing and generated outputs contain no numeric model value. Each
horizon returns an ordinal illustrative simulation category, explanation,
basis, status, and
`target_outcome: "not_defined_pending_clinical_review"`. **Target outcome is
not defined pending clinical review.** The categories are illustrative only
and are withheld when any of these required baseline inputs is unavailable:

- cancer stage;
- ECOG;
- reduced appetite;
- BMI; or
- baseline weight change.

Sex and lung subtype are descriptive/future-use fields and do not alter the
current category. Sarcopenia remains a tri-state future-use field pending a
clinical definition; it is never inferred, its baseline value does not decide
a future label, and it does not alter the category. When weight loss is >2%
and <=5%, BMI is >=20, and the sarcopenia branch is disabled, criteria status
is `unknown`, not `no`, because the unevaluated third branch could change the
result.

## Clinical and temporal framing

Fearon et al. (2011) describes **>5% weight loss over the past 6 months**.
Accordingly, this project separates retrospective baseline-derived status from
future synthetic outcomes:

- baseline status uses eligible retrospective weight evidence up to six
  months;
- the 3-month baseline-to-horizon label is explicitly a research-only
  threshold-based outcome that differs from Fearon in both direction and
  window length; and
- although the 6-month label matches the six-month window length, it looks
  forward from baseline and is not a Fearon classification; it is a
  prospective research endpoint only, not a diagnosis.

Both future outcome objects record `fearon_classification: false` and the
actual `outcome_interval_days` from baseline weight date to selected outcome
weight date. Baseline sarcopenia is never reused as future evidence.

Future provisional pre-cachexia labels use dated synthetic follow-up appetite
observations. Baseline `reduced_appetite` remains a predictor and is never
carried forward as future observed evidence.

The provisional candidate rule is cachexia criteria excluded, loss **>1% and
<=5%**, and reduced appetite=`yes`. The >1% lower bound has no consensus basis
and remains an editable simulation parameter; <=5% is consensus-aligned.
Binary appetite is a POC simplification.

References:

- Fearon K, et al. *Lancet Oncology*. 2011;12(5):489-495.
  <https://doi.org/10.1016/S1470-2045(10)70218-7>
- Muscaritoli M, et al. *Clinical Nutrition*. 2010;29(2):154-159.
  <https://doi.org/10.1016/j.clnu.2009.12.004>

## Run and regenerate

Python 3.9 or newer is required for the core project. Workbook generation
requires the declared optional dependencies.

```bash
PYTHONPATH=src python3 scripts/generate_synthetic.py \
  --count 120 --seed 20260820
python3 scripts/sync_browser_config.py
python3 scripts/build_excel_prototype.py
python3.12 -m pip install -e '.[vba]'
python3.12 scripts/build_excel_vba_prototype.py
python3.12 scripts/build_clinical_logic_review.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --test tests/browser_calculations.test.js
python3 scripts/run_local.py
```

Open <http://127.0.0.1:8000> for local development. The page can also be
opened directly from `prototype/index.html`.

The Excel files remain repository/local review artifacts:

- `excel/cachexia_risk_prototype.v1.4.xlsx` is macro-free;
- `excel/cachexia_risk_mock_ui.v1.1.xlsm` provides native form controls; and
- `excel/clinical_logic_review_matrix.v1.xlsx` records unresolved review
  questions and the exhaustive classification matrix.

The Pages workflow rebuilds and tests the workbooks but publishes only the
static browser files. It does not copy workbook files into the Pages artifact.

## Key implementation paths

| Deliverable | Path |
|---|---|
| Browser prototype | `prototype/index.html`, `prototype/app.js`, `prototype/calculations.js` |
| Python calculations | `src/cachexia_poc/` |
| Central assumptions | `config/simulation_assumptions.v1.json` |
| Generated browser config | `prototype/simulation-config.js` |
| Generated cohort and summary | `data/` |
| Formal schema and migration note | `docs/schema.v1.json` |
| Workbook builders | `scripts/build_excel_prototype.py`, `scripts/build_excel_vba_prototype.py`, `scripts/build_clinical_logic_review.py` |
| Review workbooks | `excel/` |
| Clinical and temporal documentation | `docs/CLINICAL_RULES.md`, `docs/FORMULAS_AND_TEMPORAL_RULES.md`, `docs/OUTCOME_IMPLEMENTATION.md` |
| Review package and test matrix | `docs/CLINICAL_REVIEW_PACKAGE.md`, `docs/CLINICAL_LOGIC_TEST_MATRIX.md` |
| Tests | `tests/` |

## Boundaries and limitations

Thresholds remain strict: >5%, >2%, and BMI <20. Predictors read only
measurements dated on or before `prediction_date`; future observations cannot
leak into baseline calculations. Loss <=2% remains `no`; loss >5% and loss
>2% with BMI <20 remain `yes`. In the >2% to <=5%, BMI >=20 interval, the
disabled sarcopenia branch leaves cachexia and provisional early-risk status
`unknown`. Unknown is never treated as no.

This is not a trained or evaluated model. There is no real cohort, agreed
eligibility definition, validated endpoint, reference standard, or evidence
supporting clinical performance. Open clinical and UX decisions remain
explicitly pending in the review package.
