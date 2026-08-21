# Candidate clinical classification rules

> **Not clinical guidance.** These rules create transparent labels for
> synthetic data. They do not establish diagnosis, prognosis, treatment
> relevance, or clinical validity.

## Baseline-derived current criteria status

Fearon et al. (2011) defines the weight-loss branch retrospectively: **>5%
weight loss over the past 6 months**. The v1 baseline-derived status uses the
oldest eligible prior weight in the six-calendar-month interval ending at the
baseline weight:

1. weight loss **>5%**; or
2. weight loss **>2%** and baseline BMI **<20 kg/m²**.

The sarcopenia field remains `yes|no|unknown` but its branch is disabled by
default in v1. It is future-use, pending a clinical definition, and never
inferred. The recorded baseline value does not decide the disabled branch or
the illustrative simulation category.

Boundaries are strict:

- exactly 5% does not satisfy the >5% branch;
- exactly 2% does not enter the conditional branch; and
- BMI exactly 20 does not satisfy BMI <20.

Missing baseline weight change makes the status unknown. BMI is needed only
when loss is in the conditional interval; missing BMI then makes the status
unknown. For loss >2% and <=5% with BMI >=20, status is also `unknown`, not
`no`: the BMI branch is not met and the sarcopenia branch is disabled pending
a clinical definition, so the unevaluated branch could change the result.
Sarcopenia does not resolve an unknown BMI in v1.

## Future research-only threshold outcomes

The future labels are not unqualified Fearon classifications:

- the 3-month label uses baseline-to-3-month change, which looks forward and
  differs from Fearon 2011 in both direction and window length; and
- although the 6-month label matches the six-month window length, it looks
  forward from baseline and is not a Fearon classification; it is a
  prospective research endpoint only, not a diagnosis.

Both retain the strict >5%, >2%, and BMI <20 thresholds only as transparent
research operationalisations. Both expose `fearon_classification: false` and
the actual baseline-to-outcome interval in days. Baseline sarcopenia is never
used as future evidence because there is no dated future sarcopenia
observation contract.

## Provisional pre-cachexia candidate

The candidate is `yes` only when:

- cachexia criteria status is `no`;
- weight loss is **>1% and <=5%**; and
- reduced appetite is explicitly `yes`.

When cachexia criteria status is `unknown`, the candidate is also `unknown`
because cachexia has not been excluded.

Muscaritoli et al. (2010) describes pre-cachexia with <=5% weight loss plus
anorexia and metabolic change. This POC's **>1% lower bound has no consensus
basis** and is an editable simulation parameter. The <=5% upper bound is
consensus-aligned. Binary appetite is a POC simplification and does not
represent the full anorexia/metabolic-change concept.

Baseline status uses baseline `reduced_appetite`. Future outcomes use only the
latest dated synthetic follow-up appetite observation within the horizon.
Baseline appetite is never carried forward as future observed evidence. When
the future weight interval otherwise matches but no horizon-specific appetite
observation exists, the future candidate label is `unknown`.

## References

- Fearon K, et al. *Lancet Oncology*. 2011;12(5):489-495.
  <https://doi.org/10.1016/S1470-2045(10)70218-7>
- Muscaritoli M, et al. *Clinical Nutrition*. 2010;29(2):154-159.
  <https://doi.org/10.1016/j.clnu.2009.12.004>

## Decisions still required

- Define eligibility and inclusion criteria.
- Confirm the retrospective baseline measurement-selection rule.
- Confirm or revise the provisional >1% lower bound and binary appetite
  representation.
- Define acceptable dated appetite evidence.
- Define sarcopenia evidence before considering a future branch.
- Confirm the 3-month and 6-month research endpoint framing.
- Define the target outcome or estimand before interpreting the ordinal
  illustrative simulation categories. Until then,
  `target_outcome` is `not_defined_pending_clinical_review`, and any
  differences between horizon categories are simulation assumptions only.
