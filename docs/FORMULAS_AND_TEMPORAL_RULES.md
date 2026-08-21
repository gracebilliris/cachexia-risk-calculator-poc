# Formulas and temporal rules

> **Synthetic research proof of concept only.** These rules are not a validated
> clinical model and must not be used for patient care.

## Prediction point and leakage boundary

Every patient has an ISO `prediction_date`. Baseline predictors may read only
measurements with `measurement.date <= prediction_date`. Future weight and
appetite observations never enter baseline predictors or the illustrative
simulation category.

Three- and six-month dates use calendar-month addition, clamping an unavailable
day to month end. A measurement exactly on a horizon date is included; one day
later is excluded. Each horizon selects the latest observation in
`(prediction_date, horizon_date]`.

## Baseline measurement selection

- Baseline weight: latest dated weight on or before prediction.
- Duplicate latest date: last input record wins.
- Prior weight: oldest measurement in the six-calendar-month interval ending
  at baseline, strictly before baseline.
- Older measurements and equal timestamps are not used as the prior value.
- No value is imputed.

Let baseline weight be `Wc` kg, prior weight `Wp` kg, height `H` metres,
elapsed days `D`, and `M = D / 30.4375`.

| Variable | Formula |
|---|---|
| BMI | `Wc / H²`, kg/m² |
| Weight loss | `(Wp - Wc) / Wp * 100`; positive means loss |
| Weight-loss rate | `(Wp - Wc) / M`, kg/month |
| Percentage-point rate | `weight loss / M`, percentage points/month |
| Interval | Exact calendar-day difference |
| Trajectory | loss if `>0.5%`; gain if `<-0.5%`; otherwise stable |

## Current status versus future outcomes

Baseline-derived criteria status uses retrospective evidence up to six months.
The 3-month future label is a research-only threshold outcome that differs from
Fearon 2011 in direction and window length. Although the 6-month future label
matches the window length, it looks forward from baseline and is not a Fearon
classification; it is a prospective research endpoint only, not a diagnosis.
Both record `fearon_classification=false` and `outcome_interval_days`, the
actual difference between selected baseline and outcome weight dates.

Future provisional labels use dated follow-up appetite observations. Baseline
`reduced_appetite` cannot change those labels. Baseline sarcopenia is likewise
never future evidence; no dated future sarcopenia observation contract exists.

For loss >2% and <=5% with BMI >=20, the disabled sarcopenia branch means
cachexia status is `unknown`, not `no`. The provisional early-risk candidate is
therefore also `unknown` because cachexia has not been excluded. Loss <=2%
remains `no`; loss >5% and loss >2% with BMI <20 remain `yes`.

## Illustrative simulation categories

Separate 3-month and 6-month internal arithmetic maps baseline predictors to
`low`, `moderate`, or `high`. Clinical-facing and generated outputs expose only
the ordinal category, explanations, basis, status, and
`target_outcome=not_defined_pending_clinical_review`. Target outcome is not
defined pending clinical review, so the categories are illustrative only.
Differences between horizons are simulation assumptions, not distinct
clinically defined estimands.

The category is withheld when any required baseline value is unavailable:

| Missing value | Recorded reason |
|---|---|
| Stage | `cancer_stage_unknown` |
| ECOG | `ecog_unknown` |
| Reduced appetite | `reduced_appetite_unknown` |
| BMI | `bmi_unavailable` |
| Baseline weight change | `baseline_weight_change_unavailable` |

Sex, lung subtype, and sarcopenia are explicitly unused. The category basis is
always `baseline_predictors_only`.
