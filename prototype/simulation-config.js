"use strict";

window.SIMULATION_CONFIG = Object.freeze({
  metadata: {
    warning: "Every value is a research-only simulation assumption."
  },
  cohort: {
    age: { minimum: 18, maximum: 95 },
    height_cm: {
      female: { minimum: 140, maximum: 190 },
      male: { minimum: 150, maximum: 200 },
      unknown: { minimum: 140, maximum: 200 }
    },
    historical_weight_kg: { minimum: 25, maximum: 160 }
  },
  definitions: {
    days_per_month: 30.4375,
    trajectory_epsilon_percent: 0.5,
    fearon_sarcopenia_branch_enabled: false,
    fearon_weight_loss_primary_exclusive: 5,
    fearon_weight_loss_conditional_exclusive: 2,
    fearon_bmi_exclusive: 20,
    precachexia_lower_weight_loss_percent_exclusive: 0,
    precachexia_upper_weight_loss_percent_inclusive: 5,
    simulation_category_missing_predictor_policy: "withhold"
  },
  illustrative_category_model: {
    age_threshold_exclusive: 55,
    internal_score_thresholds: {
      high_lower_inclusive: 0.4054651081081642,
      low_upper_exclusive: -0.8472978603872036
    },
    output_contract: {
      basis: "baseline_predictors_only",
      output_type: "illustrative_simulation_category",
      target_outcome: "incident_pre_cachexia_or_cachexia",
      unused_fields: ["sex", "cancer_subtype", "sarcopenia"]
    },
    three_month: {
      age_over_55: 0.25,
      appetite: { no: 0, unknown: 0.15, yes: 0.75 },
      baseline_weight_loss_per_percent: 0.13,
      cancer_type_multiplier: 1,
      ecog: { 0: -0.3, 1: 0, 2: 0.35, 3: 0.7, 4: 1, unknown: 0 },
      intercept: -2,
      low_bmi_under_20: 0.45,
      stage: { I: 0, II: 0.2, III: 0.5, IV: 1, unknown: 0 }
    },
    six_month: {
      age_over_55: 0.3,
      appetite: { no: 0, unknown: 0.15, yes: 0.8 },
      baseline_weight_loss_per_percent: 0.15,
      cancer_type_multiplier: 1,
      ecog: { 0: -0.25, 1: 0, 2: 0.4, 3: 0.8, 4: 1.1, unknown: 0 },
      intercept: -1.45,
      low_bmi_under_20: 0.5,
      stage: { I: 0, II: 0.2, III: 0.5, IV: 1, unknown: 0 }
    }
  },
  simulation_relationships: {
    cancer_risk_multipliers: {
      breast: 1,
      colorectal: 1.3,
      gastric: 1.8,
      "head and neck": 1.6,
      hepatobiliary: 2,
      lung: 1.6,
      oesophageal: 1.8,
      "other solid tumour": 1,
      pancreatic: 2,
      prostate: 1
    },
    cancer_stage_interaction: { strength: 1 },
    stage_risk_multipliers: {
      I: 1,
      II: 1.2,
      III: 1.5,
      IV: 2,
      unknown: 1
    }
  }
});
