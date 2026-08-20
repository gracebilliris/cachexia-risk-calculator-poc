# Formulas and temporal rules

> **Synthetic research proof of concept only.** These rules do not constitute a
> validated clinical model and must not be used for patient care.

## Prediction point and leakage boundary

Every patient has an ISO `prediction_date`. Predictor construction may read
only measurements with `measurement.date <= prediction_date`. Outcome
engineering may read measurements after the prediction date, but those values
never enter baseline predictors or simulated risk scores.

Three- and six-month horizon dates are obtained by adding calendar months and
clamping an unavailable day to month end (for example, 31 January + 3 months =
30 April). A measurement exactly on a horizon date is included; one day later
is excluded. The latest measurement in `(prediction_date, horizon_date]` is the
outcome weight.

## Measurement selection

- **Current/baseline weight:** latest dated weight on or before prediction.
- **Duplicate latest date:** last input record wins, making resolution
  deterministic while surfacing the need for source-system deduplication.
- **Prior weight:** oldest measurement in the six-calendar-month interval
  ending at the baseline measurement, strictly before baseline. This maximises
  observable look-back. Duplicate prior dates use the last input record.
- A measurement older than six calendar months is not used.
- Equal timestamps never create a zero-duration rate; no prior value is
  returned unless its date is earlier.

## Derived variables

Let current weight be `Wc` kg, prior weight `Wp` kg, height `H` metres, elapsed
days `D`, and `M = D / 30.4375`.

| Variable | Formula and sign |
|---|---|
| BMI | `Wc / H²`, kg/m² |
| Percentage weight loss | `(Wp - Wc) / Wp * 100`; positive means loss, negative means gain |
| Weight-loss rate | `(Wp - Wc) / M`, kg/month |
| Percentage-point rate | `percentage weight loss / M`, percentage points/month |
| Interval | Exact calendar-day difference, `D` |
| Trajectory | loss if total loss `>0.5%`; gain if `<-0.5%`; otherwise stable |

The 0.5% trajectory tolerance is an editable **simulation assumption** in
`config/simulation_assumptions.v1.json`.

If baseline weight is absent, all derived values are unknown. If height is
unknown, BMI alone is unknown. If no eligible prior weight exists, change,
interval, rates, and trajectory are not calculable. Irregular intervals use
actual elapsed days. No value is imputed.
