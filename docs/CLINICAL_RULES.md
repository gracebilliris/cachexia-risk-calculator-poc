# Candidate clinical classification rules

> **Not clinical guidance.** This document describes transparent labels for
> synthetic data. It does not establish diagnosis, prognosis, treatment
> relevance, or clinical validity.

## Fearon cachexia implementation

The POC encodes three Fearon branches:

1. weight loss **>5%**, or
2. weight loss **>2%** and current BMI **<20 kg/m²**, or
3. weight loss **>2%** with explicitly documented sarcopenia evidence.

Thresholds are strict: exactly 5% does not satisfy branch 1; exactly 2% does
not satisfy branch 2; BMI exactly 20 does not satisfy branch 2.
Weight loss is measured from prediction-date baseline to the latest weight in
the selected future horizon. This is a POC operationalisation and requires
clinical confirmation.

Sarcopenia is entered as `yes`, `no`, or `unknown`. It must represent
independently documented evidence and is never inferred from BMI, ECOG, cancer,
stage, appetite, or weight. The schema does not specify CT muscle index,
sex-specific thresholds, or another assessment method. For synthetic horizon
labels, the baseline sarcopenia value is carried forward as a provisional
operational assumption; clinical reviewers must confirm whether a dated
horizon-specific assessment is required.

| Situation | Cachexia result |
|---|---|
| Loss >5% | yes |
| Loss <=2% | no |
| Loss >2%, BMI <20 | yes |
| Loss >2%, documented sarcopenia=yes | yes |
| Loss >2%, BMI >=20 and sarcopenia=no | no |
| Loss >2%, BMI >=20 and sarcopenia=unknown | unknown |
| Loss >2%, BMI unknown and sarcopenia=no/unknown | unknown |
| Missing baseline or in-horizon weight | unknown |

## Provisional pre-cachexia candidate

**Working assumption: Option B, requiring review by clinical reviewers.** It
remains separate from the Fearon label. The provisional rule is:

- cachexia has been evaluated as `no`;
- involuntary weight loss is **>1% and <=5%**; and
- reduced appetite is explicitly `yes`.

The 1% lower boundary and 5% upper boundary are editable simulation
assumptions, not validated clinical effects. Appetite `unknown` produces
`unknown` when the weight interval otherwise matches. If cachexia is unknown,
candidate pre-cachexia is unknown. No/unknown is never collapsed.

## Clinical decisions still required

- Confirm the supplied age, height, BMI, weight, stage, and ECOG
  distributions beyond the provisional workbook suggestions.
- Confirm whether outcome loss should use baseline-to-horizon weight or another
  assessment window/measurement-selection rule.
- Confirm the candidate pre-cachexia lower threshold, upper threshold,
  involuntary-loss representation, and appetite definition.
- Confirm what constitutes documented sarcopenia evidence and whether a dated
  horizon-specific assessment is required rather than carrying baseline
  evidence forward.
- Confirm whether a negative cachexia result is appropriate when all supported
  branches are refuted but unsupported clinical domains remain unavailable.
