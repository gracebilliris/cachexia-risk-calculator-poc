# Outcome implementation notes

`src/cachexia_poc/outcomes.py` is the executable source of truth.

Each horizon is evaluated independently. The three-month function cannot see
six-month measurements because its inclusive cutoff is the three-month
calendar date. This is tested by changing a six-month weight and asserting
byte-for-byte equality of the three-month result.

The result records the horizon date, included measurement date, baseline and
outcome weights, percentage loss, outcome BMI, tri-state Fearon label,
tri-state provisional pre-cachexia label, and human-readable branch trace.

The implementation uses the >5% loss, >2% loss with BMI <20, and >2% loss
with explicitly documented sarcopenia branches. Sarcopenia is tri-state and
never inferred. When BMI does not satisfy its branch and sarcopenia is
`unknown`, cachexia remains `unknown`; this also prevents a forced
pre-cachexia classification. Carrying baseline sarcopenia evidence into each
synthetic horizon is a provisional operational assumption requiring clinical
review. Candidate pre-cachexia uses the provisional early-risk rule (>1% and
<=5% loss plus reduced appetite) only after cachexia is excluded.

These are synthetic outcome labels, not predictions. The separate simulated
risk outputs are calculated from baseline predictors only and are explicitly
labelled assumptions. Neither labels nor risk estimates are clinically
validated.
