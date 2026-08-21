# Synthetic dataset data dictionary

All records are synthetic. `docs/schema.v1.json` is the formal interchange
schema; schema/config version 1.1 separates current status, future outcomes,
and baseline-only categories.

| Field | Type / unit | Meaning |
|---|---|---|
| `patient_id` | string | `SYN-*` synthetic identifier |
| `prediction_date` | ISO date | Baseline predictor cutoff |
| `age` | integer, years | 18-95 |
| `sex` | category | female / male / unknown; descriptive and unused in category |
| `cancer_type` | category | Synthetic adult solid-tumour stratifier pending review |
| `cancer_subtype` | category | SCLC / NSCLC / unknown for lung; `not applicable` otherwise; descriptive and unused |
| `cancer_stage` | category | I / II / III / IV / unknown |
| `height_cm` | number/null | Optional; required for BMI and category display |
| `weights[]` | dated kg | Longitudinal synthetic weight observations |
| `ecog` | integer/null | 0-4; null means unknown |
| `reduced_appetite` | tri-state | Baseline predictor only; never carried into future evidence |
| `sarcopenia` | tri-state | Future-use, pending definition, never inferred; baseline value is never future evidence |
| `follow_up_appetite_observations[]` | dated tri-state + source | Synthetic future evidence used only by future candidate labels; `source` must equal `synthetic_follow_up_observation` |
| `baseline_predictors` | object | Baseline-only derived variables |
| `baseline_criteria_status` | object | Current baseline-derived cachexia and provisional candidate status |
| `outcome_3m` | object | Research-only 3-month threshold outcome; `fearon_classification=false`; differs from Fearon in direction/window |
| `outcome_6m` | object | Prospective 6-month research endpoint only; `fearon_classification=false`; not a Fearon classification or diagnosis |
| `outcome_interval_days` | integer/null | Actual days from selected baseline weight date to selected outcome weight date |
| `illustrative_simulation_3m` | object | Baseline-only ordinal category or withheld, with reasons and undefined target outcome |
| `illustrative_simulation_6m` | object | Separate baseline-only ordinal category or withheld, with the same undefined target outcome |
| `provenance` | object | Synthetic/config/schema/migration status |

Category objects expose no numeric model value. Their permitted category is
`low`, `moderate`, `high`, or `null` when withheld. Required withholding
reasons cover unknown stage, ECOG, appetite, unavailable BMI, and unavailable
baseline weight change. Every category object includes
`target_outcome: "not_defined_pending_clinical_review"`; target outcome is not
defined pending clinical review, and the categories are illustrative only.

The CSV flattens status/category/basis fields and stores longitudinal arrays as
compact JSON strings. The JSON file is canonical because it preserves nested
explanations and provenance.

## Unknown behavior

Unknown is never encoded as no. JSON uses `null` for unknown ECOG and
`"unknown"` for tri-state categories. Derived values use `null` when not
calculable. For loss >2% and <=5% with BMI >=20, the disabled sarcopenia branch
leaves cachexia and provisional early-risk status unknown. No real or
identifiable health information is included.

## Population status

Eligibility and inclusion criteria remain undefined. Cancer labels are
synthetic stratifiers for an adult solid-tumour POC pending clinical review;
they do not imply an agreed diagnosis, treatment state, or exclusion rule.
