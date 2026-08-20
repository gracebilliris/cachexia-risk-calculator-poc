# Outcome implementation notes

`src/cachexia_poc/outcomes.py` is the executable source of truth.

Each horizon is evaluated independently. The three-month function cannot see
six-month measurements because its inclusive cutoff is the three-month
calendar date. This is tested by changing a six-month weight and asserting
byte-for-byte equality of the three-month result.

The result records the horizon date, included measurement date, baseline and
outcome weights, percentage loss, outcome BMI, tri-state Fearon label,
tri-state provisional pre-cachexia label, and human-readable branch trace.

V1 uses the >5% loss and >2% loss with BMI <20 branches only. Sarcopenia
remains in the schema for later use but cannot alter a v1 label. Candidate
pre-cachexia uses provisional Option B (>1% and <=5% loss plus reduced
appetite) after cachexia is excluded.

These are synthetic outcome labels, not predictions. The separate simulated
risk outputs are calculated from baseline predictors only and are explicitly
labelled assumptions. Neither labels nor risk estimates are clinically
validated.
