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
    const categoryModel = config.illustrative_category_model;
    const assumptions = Object.freeze({
      monthDays: definitions.days_per_month,
      trajectoryEpsilonPercent: definitions.trajectory_epsilon_percent,
      ageThresholdExclusive: categoryModel.age_threshold_exclusive,
      sarcopeniaBranchEnabled: definitions.fearon_sarcopenia_branch_enabled,
      fearon: {
        primaryLossExclusive: definitions.fearon_weight_loss_primary_exclusive,
        conditionalLossExclusive: definitions.fearon_weight_loss_conditional_exclusive,
        bmiExclusive: definitions.fearon_bmi_exclusive
      },
      precachexia: {
        lowerExclusive: definitions.precachexia_lower_weight_loss_percent_exclusive,
        upperInclusive: definitions.precachexia_upper_weight_loss_percent_inclusive
      },
      categoryThresholds: categoryModel.internal_score_thresholds,
      cancerMultipliers: config.simulation_relationships.cancer_risk_multipliers,
      stageMultipliers: config.simulation_relationships.stage_risk_multipliers,
      interactionStrength:
        config.simulation_relationships.cancer_stage_interaction.strength,
      categoryModel
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
      if (derived.loss === null || derived.loss === undefined) {
        return {
          cachexiaCriteria: "unknown — insufficient eligible weight history",
          precachexiaCandidate: "unknown — insufficient eligible weight history",
          clinicalState: "Unknown"
        };
      }
      const rule = assumptions.fearon;
      const approximately = (left, right) => Math.abs(left - right) < 1e-9;
      let fearon;
      if (
        derived.loss > rule.primaryLossExclusive
        && !approximately(derived.loss, rule.primaryLossExclusive)
      ) {
        fearon = "yes — retrospective weight loss >5%";
      } else if (
        derived.loss < rule.conditionalLossExclusive
        || approximately(derived.loss, rule.conditionalLossExclusive)
      ) {
        fearon = "no — supported branches require >2% loss";
      } else if (derived.bmi !== null && derived.bmi < rule.bmiExclusive) {
        fearon = "yes — loss >2% and BMI <20";
      } else if (derived.bmi !== null) {
        fearon = "no — loss is >2% and ≤5%, but BMI is ≥20";
      } else {
        fearon = "unknown — BMI unavailable for the >2% conditional branch";
      }

      const preRule = assumptions.precachexia;
      let pre;
      if (fearon.startsWith("unknown")) {
        pre = "unknown — cachexia not evaluable";
      } else if (fearon.startsWith("yes")) {
        pre = "no — cachexia criterion takes precedence";
      } else if (!(
        derived.loss > preRule.lowerExclusive
        && (
          derived.loss < preRule.upperInclusive
          || approximately(derived.loss, preRule.upperInclusive)
        )
      )) {
        pre = "no — outside provisional synthetic loss interval";
      } else if (input.appetite === "yes") {
        pre = "yes — provisional synthetic positive loss + baseline appetite rule";
      } else if (input.appetite === "no") {
        pre = "no — appetite explicitly absent";
      } else {
        pre = "unknown — appetite unknown";
      }
      const clinicalState = fearon.startsWith("yes")
        ? "Cachexia"
        : fearon.startsWith("unknown")
          ? "Unknown"
          : pre.startsWith("yes")
            ? "Pre-cachexia"
            : pre.startsWith("unknown")
              ? "Unknown"
              : "No cachexia";
      return {
        cachexiaCriteria: fearon,
        precachexiaCandidate: pre,
        clinicalState
      };
    }

    function category(input, derived, horizon) {
      const terms = assumptions.categoryModel[horizon];
      if (!terms) throw new Error(`Unsupported simulation horizon: ${horizon}`);
      const horizonMonths = horizon === "three_month" ? 3 : 6;
      const missing = [];
      const explanations = [];
      if (input.stage === "unknown") {
        missing.push("cancer_stage_unknown");
        explanations.push("Cancer stage is unknown.");
      }
      if (input.ecog === "unknown") {
        missing.push("ecog_unknown");
        explanations.push("Baseline ECOG is unknown.");
      }
      if (input.appetite === "unknown") {
        missing.push("reduced_appetite_unknown");
        explanations.push("Baseline reduced appetite is unknown.");
      }
      if (derived.bmi === null) {
        missing.push("bmi_unavailable");
        explanations.push(
          "BMI is unavailable because height or baseline weight is unavailable."
        );
      }
      if (derived.loss === null) {
        missing.push("baseline_weight_change_unavailable");
        explanations.push(
          "Baseline weight change is unavailable because eligible prior weight history is insufficient."
        );
      }
      const classification = classify(input, derived);
      if (input.activeCancer === false) {
        missing.push("cancer_not_active");
        explanations.push("Active solid cancer is required.");
      }
      if (!["I", "II", "III", "IV"].includes(input.stage)) {
        missing.push("stage_not_I_to_IV");
        explanations.push("Stage I-IV is required for incident-risk eligibility.");
      }
      if (classification.clinicalState === "Cachexia") {
        missing.push("ineligible_baseline_cachexia");
        explanations.push(
          "Baseline-cachectic patients are retained for classification testing but excluded from incident-risk modeling."
        );
      }
      if (classification.cachexiaCriteria.startsWith("unknown")) {
        missing.push("baseline_cachexia_not_excluded");
        explanations.push("Incident-risk eligibility is indeterminate.");
      }
      const contract = assumptions.categoryModel.output_contract;
      const common = {
        horizonMonths,
        outputType: contract.output_type,
        basis: contract.basis,
        target_outcome: contract.target_outcome,
        unusedFields: contract.unused_fields
      };
      if (
        config.definitions.simulation_category_missing_predictor_policy
          === "withhold"
        && missing.length
      ) {
        return {
          ...common,
          category: null,
          status: "withheld_missing_required_baseline_predictors",
          withholdingReasons: missing,
          explanations: [
            `${horizonMonths}-month illustrative simulation category withheld.`,
            ...explanations
          ]
        };
      }
      let internalValue = terms.intercept;
      const factors = [];
      if (input.age > assumptions.ageThresholdExclusive) {
        internalValue += terms.age_over_55;
        factors.push("Age over 55");
      }
      internalValue += terms.stage[input.stage];
      if (terms.stage[input.stage]) {
        factors.push(`Cancer stage ${input.stage}`);
      }
      internalValue += terms.ecog[input.ecog];
      if (terms.ecog[input.ecog]) {
        factors.push(`ECOG ${input.ecog}`);
      }
      internalValue += terms.appetite[input.appetite];
      if (terms.appetite[input.appetite]) {
        factors.push(`Reduced appetite: ${input.appetite}`);
      }
      if (derived.loss !== null && derived.loss > 0) {
        internalValue += derived.loss * terms.baseline_weight_loss_per_percent;
        factors.push(`Weight loss: ${derived.loss.toFixed(1)}%`);
      }
      if (
        derived.bmi !== null
        && derived.bmi < assumptions.fearon.bmiExclusive
      ) {
        internalValue += terms.low_bmi_under_20;
        factors.push("BMI below 20");
      }
      const cancer = (assumptions.cancerMultipliers[input.cancerType] - 1)
        * terms.cancer_type_multiplier;
      internalValue += cancer;
      if (cancer) factors.push(`Cancer type: ${input.cancerType}`);
      const interaction = (
        (assumptions.stageMultipliers[input.stage] - 1)
        * (assumptions.cancerMultipliers[input.cancerType] - 1)
        * assumptions.interactionStrength
        * terms.cancer_type_multiplier
      );
      internalValue += interaction;
      if (interaction) {
        factors.push(
          "Combined cancer type and stage factor"
        );
      }
      const simulationCategory = (
        internalValue < assumptions.categoryThresholds.low_upper_exclusive
        ? "low"
        : internalValue >= assumptions.categoryThresholds.high_lower_inclusive
          ? "high"
          : "moderate"
      );
      return {
        ...common,
        category: simulationCategory,
        status: contract.status,
        withholdingReasons: [],
        explanations: [
          `${horizonMonths}-month illustrative simulation category based on baseline predictors only.`,
          ...(factors.length
            ? factors
            : ["No additional category factors were active."])
        ]
      };
    }

    return { addMonths, calculateDerived, classify, category };
  }

  return { cancerSubtypeOptions, createCalculator };
}));
