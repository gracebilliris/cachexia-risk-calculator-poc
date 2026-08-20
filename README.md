# Synthetic cachexia risk proof of concept

> **Research-only and not for clinical use.** All patients and outputs are
> synthetic. Every risk relationship, coefficient, probability, multiplier,
> threshold, and score is a simulation assumption. This project is not
> clinically validated and must not be used for diagnosis, prognosis,
> treatment, patient care, or medical decisions.

This dependency-free Python/static-web POC explores separate three- and
six-month cachexia and provisional pre-cachexia simulation outputs. It uses the
proposed synthetic ranges in `Data Extraction_literature review_20260728.xlsx`
where available and labels additional assumptions for clinical confirmation.
The source literature workbook is intentionally retained outside this
repository and is excluded by `.gitignore`; the generated synthetic Excel
prototype is included.

**Live synthetic demonstrator:** <https://gracebilliris.github.io/cachexia-risk-calculator-poc/>

## Run

Python 3.9 or newer is required. The browser/Python prototype has no runtime
packages; rebuilding the macro-free Excel workbook requires `openpyxl`.
Rebuilding the separate VBA mock UI requires Python 3.10 or newer plus the
`vba` optional dependencies.

```bash
PYTHONPATH=src python3 scripts/generate_synthetic.py \
  --count 120 --seed 20260820
python3 scripts/sync_browser_config.py
python3 scripts/build_excel_prototype.py
python3.12 -m pip install -e '.[vba]'
python3.12 scripts/build_excel_vba_prototype.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --test tests/browser_calculations.test.js
python3 scripts/run_local.py
```

Open <http://127.0.0.1:8000> for local development. The development server
binds to loopback only. The static page can also be opened directly from
`prototype/index.html`.

The page is interactive: change factors or dated weights and press **Calculate
simulated outputs**. Two independent Excel editions are provided:

- `cachexia_risk_prototype.v1.4.xlsx` is macro-free and maximizes portability.
- `cachexia_risk_mock_ui.v1.1.xlsm` uses native Form Control buttons for
  **Calculate / validate**, **Reset form**, example profiles, and review
  navigation. Each input has an adjacent valid-value descriptor. Cancer
  subtype changes to `SCLC / NSCLC / unknown` for lung cancer and
  `not applicable` otherwise. Enable macros only after confirming the file
  came from this repository or its GitHub Pages site. Inputs, dropdowns, formulas, and outputs
  still work if macros remain disabled.

The GitHub Pages deployment runs the JavaScript calculation module generated
from the canonical simulation assumptions. It does not run a Python service or
send entered data to this repository. The deployment workflow rebuilds and
tests both Excel editions and publishes them as downloads with the static site.

## Key implementation paths

| Deliverable | Path |
|---|---|
| Browser prototype | `prototype/index.html`, `prototype/app.js`, `prototype/calculations.js`, `prototype/styles.css` |
| Macro-free Excel prototype | `excel/cachexia_risk_prototype.v1.4.xlsx` |
| VBA mock UI | `excel/cachexia_risk_mock_ui.v1.1.xlsm` |
| VBA source | `vba/CachexiaUI.bas` |
| Generator | `src/cachexia_poc/generator.py`, `scripts/generate_synthetic.py` |
| Central assumptions | `config/simulation_assumptions.v1.json` |
| Generated browser config | `prototype/simulation-config.js` (do not edit manually) |
| Sample JSON/CSV | `data/synthetic_patients.v1.json`, `data/synthetic_patients.v1.csv` |
| Distribution summary | `data/distribution_summary.v1.json` |
| Formal schema | `docs/schema.v1.json` |
| Data dictionary | `docs/DATA_DICTIONARY.md` |
| Formulas/temporal rules | `docs/FORMULAS_AND_TEMPORAL_RULES.md` |
| Fearon/pre-cachexia notes | `docs/CLINICAL_RULES.md`, `docs/OUTCOME_IMPLEMENTATION.md` |
| Clinical review package | `docs/CLINICAL_REVIEW_PACKAGE.md` |
| Tests | `tests/` |
| Final report | `docs/IMPLEMENTATION_REPORT.md` |

## Temporal and missing-data guarantees

Baseline predictors use only measurements dated on or before each patient's
explicit `prediction_date`. Three- and six-month outcomes use separate
inclusive calendar boundaries. Automated tests mutate post-baseline and
six-month measurements to prove they cannot change baseline or three-month
results.

Unknown ECOG, appetite, sarcopenia, BMI, and non-calculable changes remain
unknown; they are never treated as no or normal. Invalid and implausible values
raise actionable errors rather than being silently corrected. Simulated risk
is withheld when BMI or baseline weight change is not calculable.

The third Fearon branch uses only explicitly documented sarcopenia=`yes` with
weight loss `>2%`. Sarcopenia is never inferred from BMI, ECOG, stage,
appetite, cancer type, or weight. It changes the criteria label only; no
simulated risk coefficient has been invented. Its acceptable assessment method
and the provisional use of baseline evidence in horizon labels await clinical
review.

## Limitations

This is an explainable simulation, not a trained or evaluated prediction
model. It has no calibration, discrimination, causal, treatment, diagnostic,
or prognostic claims. Workbook proposals remain adjustable and the provisional
pre-cachexia definition, Fearon operationalisation, distributions,
relationships, horizon rules, and presentation await clinical-reviewer and clinical-reviewer's
documented clinical review.

The automated suite tests arithmetic, temporal leakage, horizon boundaries,
unknown handling, reproducibility, configuration parity, browser calculations,
and workbook structure/formulas. It does **not** perform clinical or
statistical hypothesis testing: there is no real cohort, prespecified clinical
hypothesis, validated endpoint, or comparator suitable for inferential claims.
