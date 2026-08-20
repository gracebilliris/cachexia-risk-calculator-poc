# Clinical review package: clinical-reviewer and clinical-reviewer

**Review status: pending — no clinical feedback or approval has been received
or recorded.**

This package concerns a synthetic, research-only POC. Risk estimates are
simulation assumptions and must not be interpreted as clinical probabilities
or used for medical decisions.

## Requested review

Please assess:

1. Whether the synthetic profiles and aggregate distributions are plausible
   enough for POC demonstrations, not whether they represent validated
   population prevalence.
2. Whether clinical-reviewer's illustrative cancer and stage multipliers, their
   multiplicative interaction, and provisional ECOG/appetite associations
   introduce misleading or implausible combinations.
3. Provisional Option B: cachexia excluded, loss >1% and <=5%, and reduced
   appetite=yes. Confirm, reject, or revise it.
4. The Fearon implementation, strict boundaries, use of horizon BMI, and
   unknown handling in `CLINICAL_RULES.md`.
5. Separate example three- and six-month labels and baseline-only simulated
   risk outputs.
6. BMI 20, weight loss 2%/5%, missing history, weight gain, unknown ECOG,
   unknown appetite, and unknown sarcopenia cases.
7. Whether any wording or visual presentation could be mistaken for a
   clinically validated calculator.

## Representative generated profiles

Generated with seed `20260820`, config `1.0.0`. `C/P` means
cachexia/provisional pre-cachexia candidate. Edge labels describe deliberately
constructed **baseline** patterns; future labels follow generated longitudinal
weights and need not match the baseline edge label.

| Synthetic ID | Labelled baseline case | Age/sex | Cancer/stage | ECOG | Appetite | Baseline BMI | Baseline loss | 3m C/P | 6m C/P | 3m simulated risk | 6m simulated risk |
|---|---|---|---|---|---|---:|---:|---|---|---|---|
| SYN-20260820-0001 | unknown fields | 87/male | gastric/IV | unknown | unknown | 41.0 | unknown | no/unknown | no/unknown | withheld/unknown | withheld/unknown |
| SYN-20260820-0002 | insufficient history | 85/male | oesophageal/III | 1 | no | 28.2 | unknown | no/no | no/no | withheld/unknown | withheld/unknown |
| SYN-20260820-0003 | weight gain | 82/male | head and neck/III | 1 | unknown | 33.5 | -3.1% | no/no | no/unknown | 37.8% medium | 52.5% medium |
| SYN-20260820-0004 | stability | 52/male | gastric/II | 1 | no | 25.4 | 0.0% | no/no | no/no | 26.9% low | 38.9% medium |
| SYN-20260820-0005 | limited loss + appetite | 73/female | head and neck/I | 2 | yes | 17.4 | 3.0% | no/no | no/no | 68.8% high | 83.2% high |
| SYN-20260820-0006 | >5% baseline loss | 76/male | prostate/IV | 2 | no | 21.3 | 6.0% | no/no | no/no | 59.4% medium | 76.0% high |
| SYN-20260820-0007 | BMI 20/loss 2 boundary | 80/male | pancreatic/III | 2 | no | 20.0 | 2.0% | yes/no | yes/no | 75.2% high | 86.4% high |
| SYN-20260820-0008 | loss 5 boundary | 56/male | pancreatic/II | 2 | no | 32.2 | 5.0% | no/no | yes/no | 61.1% high | 76.9% high |

The complete cohort is in `data/synthetic_patients.v1.json`; aggregate counts
are in `data/distribution_summary.v1.json`.

## Decision log to complete

| ID | Decision requested | Owner(s) | Current status |
|---|---|---|---|
| CLIN-001 | Confirm or revise predictor ranges/distributions | clinical-reviewer, clinical-reviewer | pending |
| CLIN-002 | Confirm stage/ECOG/appetite simulation relationships | clinical-reviewer, clinical-reviewer | pending |
| CLIN-003 | Confirm/reject/revise Option B (>1% and <=5% loss plus appetite=yes) and its missing behavior | clinical-reviewer, clinical-reviewer | pending |
| CLIN-004 | Confirm Fearon operationalisation and negative/unknown truth table | clinical-reviewer, clinical-reviewer | pending |
| CLIN-005 | Confirm outcome measurement-selection and inclusive boundaries | clinical-reviewer, clinical-reviewer | pending |
| CLIN-006 | Confirm sarcopenia remains stored but unused in v1 and whether later dated muscle measures are needed | clinical-reviewer, clinical-reviewer | pending |
| UX-001 | Identify clinically misleading language or presentation | clinical-reviewer, clinical-reviewer | pending |

Record decisions using `review_decisions.schema.json`; include rationale,
effective date, reviewer, and exact config/code changes requested. Absence of a
recorded decision is not approval.
