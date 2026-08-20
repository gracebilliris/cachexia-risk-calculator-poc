"use strict";

(function expose(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.CachexiaCalculations = api;
}(typeof globalThis !== "undefined" ? globalThis : this, function buildApi() {
  function cancerSubtypeOptions(cancerType) {
    return cancerType === "lung"
      ? ["SCLC", "NSCLC", "unknown"]
      : ["not applicable"];
  }

  function createCalculator(config) {
    if (!config?.metadata?.warning?.toLowerCase().includes("simulation assumption")) {
      throw new Error("A labelled simulation configuration is required.");
    }
    const definitions = config.definitions;
    const assumptions = Object.freeze({
      monthDays: definitions.days_per_month,
      trajectoryEpsilonPercent: definitions.trajectory_epsilon_percent,
      ageThresholdExclusive: config.risk_outputs.age_threshold_exclusive,
      fearon: {
        primaryLossExclusive: definitions.fearon_weight_loss_primary_exclusive,
        conditionalLossExclusive: definitions.fearon_weight_loss_conditional_exclusive,
        bmiExclusive: definitions.fearon_bmi_exclusive
      },
      precachexia: {
        lowerExclusive: definitions.precachexia_lower_weight_loss_percent_exclusive,
        upperInclusive: definitions.precachexia_upper_weight_loss_percent_inclusive
      },
      band: config.risk_outputs.band_thresholds,
      cancerMultipliers: config.simulation_relationships.cancer_risk_multipliers,
      risk: config.risk_outputs
    });

    function dateAtUtc(value) {
      return value ? new Date(`${value}T00:00:00Z`) : null;
    }

    function addMonths(value, months) {
      const source = dateAtUtc(value);
      const day = source.getUTCDate();
      const result = new Date(Date.UTC(
        source.getUTCFullYear(), source.getUTCMonth() + months, 1
      ));
      const monthEnd = new Date(Date.UTC(
        result.getUTCFullYear(), result.getUTCMonth() + 1, 0
      )).getUTCDate();
      result.setUTCDate(Math.min(day, monthEnd));
      return result;
    }

    function calculateDerived(input) {
      const cutoff = dateAtUtc(input.predictionDate);
      const eligible = input.weights.filter(
        (item) => dateAtUtc(item.date) <= cutoff
      );
      eligible.sort(
        (a, b) => dateAtUtc(a.date) - dateAtUtc(b.date) || a.index - b.index
      );
      const baseline = eligible.at(-1);
      const unknown = {
        baseline: null, prior: null, bmi: null, loss: null, days: null,
        kgRate: null, percentRate: null, trajectory: "unknown"
      };
      if (!baseline) return unknown;
      const lower = addMonths(baseline.date, -6);
      const priorCandidates = eligible.filter(
        (item) => dateAtUtc(item.date) >= lower
          && dateAtUtc(item.date) < dateAtUtc(baseline.date)
      );
      priorCandidates.sort(
        (a, b) => dateAtUtc(a.date) - dateAtUtc(b.date) || b.index - a.index
      );
      const prior = priorCandidates[0] || null;
      const bmi = input.height === null
        ? null
        : baseline.weightKg / ((input.height / 100) ** 2);
      if (!prior) return { ...unknown, baseline, bmi };
      const days = (
        dateAtUtc(baseline.date) - dateAtUtc(prior.date)
      ) / 86400000;
      const kgLoss = prior.weightKg - baseline.weightKg;
      const loss = kgLoss / prior.weightKg * 100;
      const months = days / assumptions.monthDays;
      return {
        baseline,
        prior,
        bmi,
        loss,
        days,
        kgRate: kgLoss / months,
        percentRate: loss / months,
        trajectory: loss > assumptions.trajectoryEpsilonPercent
          ? "loss"
          : loss < -assumptions.trajectoryEpsilonPercent
            ? "gain"
            : "stable"
      };
    }

    function classify(input, derived) {
      if (!derived.baseline || derived.loss === null) {
        return {
          fearon: "unknown — insufficient eligible weight history",
          pre: "unknown — insufficient eligible weight history"
        };
      }
      const rule = assumptions.fearon;
      let fearon;
      if (derived.loss > rule.primaryLossExclusive) {
        fearon = "yes — weight loss >5%";
      } else if (derived.loss <= rule.conditionalLossExclusive) {
        fearon = "no — supported branches require >2% loss";
      } else if (derived.bmi !== null && derived.bmi < rule.bmiExclusive) {
        fearon = "yes — loss >2% and BMI <20";
      } else if (derived.bmi !== null && derived.bmi >= rule.bmiExclusive) {
        fearon = "no — BMI branch refuted; sarcopenia reserved for later";
      } else {
        fearon = "unknown — BMI or sarcopenia branch not evaluable";
      }

      const preRule = assumptions.precachexia;
      let pre;
      if (fearon.startsWith("unknown")) {
        pre = "unknown — cachexia not evaluable";
      } else if (fearon.startsWith("yes")) {
        pre = "no — cachexia criterion takes precedence";
      } else if (!(
        derived.loss > preRule.lowerExclusive
        && derived.loss <= preRule.upperInclusive
      )) {
        pre = "no — outside provisional loss interval";
      } else if (input.appetite === "yes") {
        pre = "yes — provisional limited loss + appetite rule";
      } else if (input.appetite === "no") {
        pre = "no — appetite explicitly absent";
      } else {
        pre = "unknown — appetite unknown";
      }
      return { fearon, pre };
    }

    function risk(input, derived, horizon) {
      const terms = assumptions.risk[horizon];
      if (!terms) throw new Error(`Unsupported risk horizon: ${horizon}`);
      if (
        config.definitions.risk_missing_predictor_policy === "withhold"
        && (derived.bmi === null || derived.loss === null)
      ) {
        return {
          probability: null,
          band: "unknown",
          factors: [
            "Estimate withheld: BMI and baseline weight change are required."
          ]
        };
      }
      let score = terms.intercept;
      const factors = [];
      if (input.age > assumptions.ageThresholdExclusive) {
        score += terms.age_over_55;
        factors.push("Age >55 simulation term");
      }
      score += terms.stage[input.stage];
      if (terms.stage[input.stage]) {
        factors.push(`Stage ${input.stage} simulation term`);
      }
      score += terms.ecog[input.ecog];
      if (terms.ecog[input.ecog]) {
        factors.push(`ECOG ${input.ecog} simulation term`);
      }
      score += terms.appetite[input.appetite];
      if (terms.appetite[input.appetite]) {
        factors.push(`Appetite=${input.appetite} simulation term`);
      }
      if (derived.loss !== null && derived.loss > 0) {
        score += derived.loss * terms.baseline_weight_loss_per_percent;
        factors.push(`Baseline loss ${derived.loss.toFixed(1)}% simulation term`);
      }
      if (
        derived.bmi !== null
        && derived.bmi < assumptions.fearon.bmiExclusive
      ) {
        score += terms.low_bmi_under_20;
        factors.push("BMI <20 simulation term");
      }
      const cancer = (assumptions.cancerMultipliers[input.cancerType] - 1)
        * terms.cancer_type_multiplier;
      score += cancer;
      if (cancer) factors.push(`${input.cancerType} simulation term`);
      const probability = 1 / (1 + Math.exp(-score));
      const band = probability < assumptions.band.low_upper_exclusive
        ? "low"
        : probability >= assumptions.band.high_lower_inclusive
          ? "high"
          : "medium";
      return {
        probability,
        band,
        factors: factors.length
          ? factors
          : ["Intercept-only simulation estimate"]
      };
    }

    return { addMonths, calculateDerived, classify, risk };
  }

  return { cancerSubtypeOptions, createCalculator };
}));
