"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");

const { cancerSubtypeOptions,
createCalculator } = require("../prototype/calculations.js");
const config = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "config", "simulation_assumptions.v1.json"),
  "utf8"
));
const clinicalCases = JSON.parse(fs.readFileSync(
  path.join(
    __dirname,
    "fixtures",
    "clinical_logic_cases.v1.json"
  ),
  "utf8"
));
const fullClinicalMatrix = JSON.parse(fs.readFileSync(
  path.join(
    __dirname,
    "..",
    "data",
    "clinical_logic_matrix.v1.json"
  ),
  "utf8"
));
const calculator = createCalculator(config);

test("lung subtype choices follow selected cancer type", () => {
  assert.deepEqual(
    cancerSubtypeOptions("lung"),
    ["SCLC", "NSCLC", "unknown"]
  );
  assert.deepEqual(cancerSubtypeOptions("pancreatic"), ["not applicable"]);
});

function input(overrides = {}) {
  return {
    predictionDate: "2026-01-31",
    age: 65,
    height: 160,
    stage: "III",
    ecog: "2",
    appetite: "yes",
    sarcopenia: "no",
    sex: "female",
    cancerType: "lung",
    cancerSubtype: "NSCLC",
    weights: [
      { date: "2025-07-31", weightKg: 80, index: 0 },
      { date: "2026-01-31", weightKg: 72, index: 1 }
    ],
    ...overrides
  };
}

test("calculates browser BMI, positive loss, interval and trajectory", () => {
  const result = calculator.calculateDerived(input());
  assert.ok(Math.abs(result.bmi - 28.125) < 1e-12);
  assert.equal(result.loss, 10);
  assert.equal(result.days, 184);
  assert.equal(result.trajectory, "loss");
});

test("post-prediction weights cannot alter browser predictors", () => {
  const baseline = input();
  const changed = input({
    weights: [
      ...baseline.weights,
      { date: "2026-02-01", weightKg: 25, index: 2 },
      { date: "2026-07-31", weightKg: 160, index: 3 }
    ]
  });
  assert.deepEqual(
    calculator.calculateDerived(baseline),
    calculator.calculateDerived(changed)
  );
});

test("missing history remains not calculable", () => {
  const result = calculator.calculateDerived(input({
    weights: [{ date: "2026-01-31", weightKg: 72, index: 0 }]
  }));
  assert.equal(result.loss, null);
  assert.equal(result.trajectory, "unknown");
  assert.match(
    calculator.classify(input(), result).cachexiaCriteria,
    /^unknown/
  );
  const category = calculator.category(input(), result, "three_month");
  assert.equal(category.category, null);
  assert.deepEqual(
    category.withholdingReasons,
    ["baseline_weight_change_unavailable"]
  );
});

test("Fearon and provisional pre-cachexia thresholds remain distinct", () => {
  const limited = calculator.calculateDerived(input({
    weights: [
      { date: "2025-07-31", weightKg: 80, index: 0 },
      { date: "2026-01-31", weightKg: 78.8, index: 1 }
    ]
  }));
  const limitedLabels = calculator.classify(input(), limited);
  assert.match(limitedLabels.cachexiaCriteria, /^no/);
  assert.match(limitedLabels.precachexiaCandidate, /^yes/);

  const cachexia = calculator.calculateDerived(input());
  assert.match(
    calculator.classify(input(), cachexia).cachexiaCriteria,
    /^yes/
  );
  assert.match(
    calculator.classify(input(), cachexia).precachexiaCandidate,
    /^no/
  );
});

test("disabled sarcopenia branch conservatively preserves unknown", () => {
  const derived = calculator.calculateDerived(input({
    weights: [
      { date: "2025-07-31", weightKg: 80, index: 0 },
      { date: "2026-01-31", weightKg: 77.6, index: 1 }
    ]
  }));
  const noSarcopenia = calculator.classify(
    input({ sarcopenia: "no", appetite: "no" }), derived
  );
  const sarcopenia = calculator.classify(
    input({ sarcopenia: "yes", appetite: "no" }), derived
  );
  const unknownSarcopenia = calculator.classify(
    input({ sarcopenia: "unknown", appetite: "no" }), derived
  );
  assert.match(noSarcopenia.cachexiaCriteria, /^unknown/);
  assert.match(noSarcopenia.precachexiaCandidate, /^unknown/);
  assert.deepEqual(sarcopenia, noSarcopenia);
  assert.deepEqual(unknownSarcopenia, noSarcopenia);
});

test("three- and six-month category outputs are ordinal and explained", () => {
  const derived = calculator.calculateDerived(input());
  const category3 = calculator.category(input(), derived, "three_month");
  const category6 = calculator.category(input(), derived, "six_month");
  assert.ok(["low", "moderate", "high"].includes(category3.category));
  assert.ok(["low", "moderate", "high"].includes(category6.category));
  assert.equal(category3.outputType, "illustrative_simulation_category");
  assert.equal(category6.basis, "baseline_predictors_only");
  assert.equal(
    category3.target_outcome,
    "not_defined_pending_clinical_review"
  );
  assert.ok(category3.explanations.length > 0);
  assert.ok(category6.explanations.length > 0);
  assert.equal(Object.hasOwn(category3, "probability"), false);
  assert.equal(Object.hasOwn(category3, "score"), false);
});

for (const [name, overrides, derivedOverrides, reason] of [
  ["stage", { stage: "unknown" }, {}, "cancer_stage_unknown"],
  ["ECOG", { ecog: "unknown" }, {}, "ecog_unknown"],
  ["appetite", { appetite: "unknown" }, {}, "reduced_appetite_unknown"],
  ["BMI", {}, { bmi: null }, "bmi_unavailable"],
  [
    "baseline weight change",
    {},
    { loss: null },
    "baseline_weight_change_unavailable"
  ]
]) {
  test(`withholds category when ${name} is unknown`, () => {
    const caseInput = input(overrides);
    const derived = {
      ...calculator.calculateDerived(caseInput),
      ...derivedOverrides
    };
    const result = calculator.category(caseInput, derived, "three_month");
    assert.equal(result.category, null);
    assert.ok(result.withholdingReasons.includes(reason));
  });
}

test("sex and lung subtype are descriptive and unused in categories", () => {
  const derived = calculator.calculateDerived(input());
  const baseline = calculator.category(input(), derived, "three_month");
  const changed = calculator.category(
    input({ sex: "unknown", cancerSubtype: "SCLC" }),
    derived,
    "three_month"
  );
  assert.deepEqual(changed, baseline);
  assert.deepEqual(
    baseline.unusedFields,
    ["sex", "cancer_subtype", "sarcopenia"]
  );
});

test("month-end calendar arithmetic is deterministic", () => {
  assert.equal(
    calculator.addMonths("2026-01-31", 3).toISOString().slice(0, 10),
    "2026-04-30"
  );
});

test("browser classifications match the supplied decision table", () => {
  for (const clinicalCase of clinicalCases.classification_cases) {
    const caseInput = input({
      predictionDate: "2026-04-30",
      height: clinicalCase.height_cm,
      appetite: clinicalCase.appetite,
      sarcopenia: clinicalCase.sarcopenia,
      weights: [
        {
          date: "2026-01-31",
          weightKg: clinicalCase.baseline_weight_kg,
          index: 0
        },
        {
          date: "2026-04-30",
          weightKg: clinicalCase.outcome_weight_kg,
          index: 1
        }
      ]
    });
    const derived = calculator.calculateDerived(caseInput);
    const result = calculator.classify(caseInput, derived);
    assert.equal(
      result.cachexiaCriteria.startsWith(clinicalCase.expected_cachexia),
      true,
      `${clinicalCase.id}: cachexia`
    );
    assert.equal(
      result.precachexiaCandidate.startsWith(
        clinicalCase.expected_precachexia
      ),
      true,
      `${clinicalCase.id}: provisional early-risk pattern`
    );
  }
});

test("browser categories match the shared documented simulation case", () => {
  const clinicalCase = clinicalCases.category_case;
  const caseInput = input({
    age: clinicalCase.patient.age,
    stage: clinicalCase.patient.cancer_stage,
    ecog: String(clinicalCase.patient.ecog),
    appetite: clinicalCase.patient.reduced_appetite,
    cancerType: clinicalCase.patient.cancer_type
  });
  const derived = {
    bmi: clinicalCase.predictors.bmi,
    loss: clinicalCase.predictors.weight_loss_percent
  };
  for (const horizon of ["three_month", "six_month"]) {
    const result = calculator.category(caseInput, derived, horizon);
    const expected = clinicalCase.expected[horizon];
    assert.equal(result.category, expected.category);
    assert.equal(Object.hasOwn(result, "probability"), false);
    assert.equal(Object.hasOwn(result, "score"), false);
  }
});

test("browser classifications match all 324 review-matrix cases", () => {
  assert.equal(fullClinicalMatrix.cases.length, 324);
  for (const clinicalCase of fullClinicalMatrix.cases) {
    const result = calculator.classify(
      input({
        appetite: clinicalCase.reduced_appetite,
        sarcopenia: clinicalCase.sarcopenia
      }),
      {
        baseline: {},
        loss: clinicalCase.weight_loss_percent,
        bmi: clinicalCase.bmi
      }
    );
    assert.equal(
      result.cachexiaCriteria.startsWith(clinicalCase.expected_cachexia),
      true,
      `${clinicalCase.case_id}: cachexia`
    );
    assert.equal(
      result.precachexiaCandidate.startsWith(
        clinicalCase.expected_early_risk
      ),
      true,
      `${clinicalCase.case_id}: provisional early-risk pattern`
    );
  }
});
