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

## Run

Python 3.9 or newer is required. The browser/Python prototype has no runtime
packages; rebuilding the Excel workbook requires `openpyxl`.

```bash
PYTHONPATH=src python3 scripts/generate_synthetic.py \
  --count 120 --seed 20260820
python3 scripts/sync_browser_config.py
python3 scripts/build_excel_prototype.py
PYTHONPATH=src python3 -m unittest discover -s tests -v
node --test tests/browser_calculations.test.js
python3 scripts/run_local.py
```

Open <http://127.0.0.1:8000>. The server binds to loopback only; no remote
hosting or network exposure is configured. The static page can also be opened
directly from `prototype/index.html`.

The page is interactive: change factors or dated weights and press **Calculate
simulated outputs**. The Excel workbook provides an independent macro-free
interface for non-technical review.

## Key implementation paths

| Deliverable | Path |
|---|---|
| Browser prototype | `prototype/index.html`, `prototype/app.js`, `prototype/calculations.js`, `prototype/styles.css` |
| Excel prototype | `excel/cachexia_risk_prototype.v1.3.xlsx` |
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
