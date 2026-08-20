# Candidate clinical classification rules

> **Not clinical guidance.** This document describes transparent labels for
> synthetic data. It does not establish diagnosis, prognosis, treatment
> relevance, or clinical validity.

## Fearon cachexia implementation

The first POC encodes only the two Fearon branches supported by its initial
predictor set:

1. weight loss **>5%**, or
2. weight loss **>2%** and current BMI **<20 kg/m²**.

Thresholds are strict: exactly 5% does not satisfy branch 1; exactly 2% does
not satisfy branch 2; BMI exactly 20 does not satisfy branch 2.
Weight loss is measured from prediction-date baseline to the latest weight in
the selected future horizon. This is a POC operationalisation and requires
clinical confirmation.

Sarcopenia is retained as `yes`, `no`, or `unknown` for a later version. It
does not affect v1 classification and is never inferred from BMI, ECOG, cancer,
stage, appetite, or weight. The current schema does not contain CT muscle
index, sex-specific muscle thresholds, or a dated muscle assessment.

| Situation | Cachexia result |
|---|---|
| Loss >5% | yes |
| Loss <=2% | no |
| Loss >2%, BMI <20 | yes |
| Loss >2%, BMI >=20 | no |
| Loss >2% and BMI is unknown | unknown |
| Missing baseline or in-horizon weight | unknown |

## Provisional pre-cachexia candidate

**Working assumption: Option B, requiring review by clinical-reviewer and clinical-reviewer.** It
remains separate from the Fearon label. The provisional rule is:

- cachexia has been evaluated as `no`;
- involuntary weight loss is **>1% and <=5%**; and
- reduced appetite is explicitly `yes`.

The 1% lower boundary and 5% upper boundary are editable simulation
assumptions, not validated clinical effects. Appetite `unknown` produces
`unknown` when the weight interval otherwise matches. If cachexia is unknown,
candidate pre-cachexia is unknown. No/unknown is never collapsed.

## Clinical decisions still required

- Confirm clinical-reviewer's intended age, height, BMI, weight, stage, and ECOG
  distributions beyond the provisional workbook suggestions.
- Confirm whether outcome loss should use baseline-to-horizon weight or another
  assessment window/measurement-selection rule.
- Confirm the candidate pre-cachexia lower threshold, upper threshold,
  involuntary-loss representation, and appetite definition.
- Confirm whether a dated horizon-specific sarcopenia assessment is required.
- Confirm whether a negative cachexia result is appropriate when all supported
  branches are refuted but unsupported clinical domains remain unavailable.
