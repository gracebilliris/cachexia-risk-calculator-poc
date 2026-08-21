# Outcome implementation notes

`src/cachexia_poc/outcomes.py` is the executable source of truth.

## Explicitly separated outputs

`evaluate_baseline_status` returns current baseline-derived criteria status
with basis `baseline_derived_current_status`.

`evaluate_horizon` returns a qualified
`research_only_threshold_based_outcome`. Each result records:

- horizon and inclusive boundary;
- baseline and selected follow-up weight evidence;
- actual `outcome_interval_days` from baseline weight date to selected outcome
  weight date;
- dated follow-up appetite evidence, if present;
- weight change and follow-up BMI;
- threshold-based cachexia status;
- provisional pre-cachexia candidate status;
- `fearon_classification: false` and framing relative to Fearon 2011; and
- explicit provenance for weight, appetite, and sarcopenia evidence.

The 3-month status states that baseline-to-horizon change differs from Fearon
2011 in direction and window length. Although the 6-month horizon matches the
window length, its status explicitly identifies it as not a Fearon
classification: it is a prospective research endpoint only, not a diagnosis.

## Temporal evidence

Three-month evaluation cannot see six-month observations. Baseline appetite is
never reused as future observed evidence. The generator creates dated
synthetic follow-up appetite observations at each horizon; future labels use
the latest eligible observation only. If no eligible appetite observation
exists, provenance is `unavailable_no_baseline_carry_forward`.

Sarcopenia remains structurally tri-state with provenance derived from the
canonical `future_use_pending_clinical_definition` configuration. No dated
future sarcopenia observation contract exists, so `evaluate_horizon` always
passes unknown future evidence and never reuses baseline sarcopenia. When the
branch is disabled and the other conditional branch is not met, the outcome
remains unknown rather than being treated as no.

## Schema migration

Schema/config version 1.1:

- adds `follow_up_appetite_observations`;
- adds `baseline_criteria_status`;
- renames future status as `threshold_based_cachexia_status`;
- adds outcome basis/status/provenance, `fearon_classification=false`, and
  `outcome_interval_days`;
- replaces exported numeric model outputs with
  `illustrative_simulation_3m/6m` ordinal objects carrying
  `target_outcome=not_defined_pending_clinical_review`; and
- marks sarcopenia as future-use pending a clinical definition.

Existing v1.0 consumers must not interpret the renamed future label as a
diagnosis and must handle a nullable category when required baseline
predictors are unavailable.
