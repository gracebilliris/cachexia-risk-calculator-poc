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
    cancerType: "lung",
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
  assert.match(calculator.classify(input(), result).fearon, /^unknown/);
  const risk = calculator.risk(input(), result, "three_month");
  assert.equal(risk.probability, null);
  assert.equal(risk.band, "unknown");
});

test("Fearon and provisional pre-cachexia thresholds remain distinct", () => {
  const limited = calculator.calculateDerived(input({
    weights: [
      { date: "2025-07-31", weightKg: 80, index: 0 },
      { date: "2026-01-31", weightKg: 77.6, index: 1 }
    ]
  }));
  const limitedLabels = calculator.classify(input(), limited);
  assert.match(limitedLabels.fearon, /^no/);
  assert.match(limitedLabels.pre, /^yes/);

  const cachexia = calculator.calculateDerived(input());
  assert.match(calculator.classify(input(), cachexia).fearon, /^yes/);
  assert.match(calculator.classify(input(), cachexia).pre, /^no/);
});

test("documented sarcopenia implements the third Fearon branch", () => {
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
  assert.match(noSarcopenia.fearon, /^no/);
  assert.match(sarcopenia.fearon, /^yes/);
  assert.equal(
    unknownSarcopenia.fearon,
    "unknown — sarcopenia evidence unavailable"
  );
});

test("three- and six-month risk outputs are independent and explained", () => {
  const derived = calculator.calculateDerived(input());
  const risk3 = calculator.risk(input(), derived, "three_month");
  const risk6 = calculator.risk(input(), derived, "six_month");
  assert.notEqual(risk3.probability, risk6.probability);
  assert.ok(risk3.probability >= 0 && risk3.probability <= 1);
  assert.ok(risk6.probability >= 0 && risk6.probability <= 1);
  assert.ok(risk3.factors.length > 0);
  assert.ok(risk6.factors.length > 0);
});

test("month-end calendar arithmetic is deterministic", () => {
  assert.equal(
    calculator.addMonths("2026-01-31", 3).toISOString().slice(0, 10),
    "2026-04-30"
  );
});

test("browser classifications match the clinical-reviewer decision table", () => {
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
      result.fearon.startsWith(clinicalCase.expected_cachexia),
      true,
      `${clinicalCase.id}: cachexia`
    );
    assert.equal(
      result.pre.startsWith(clinicalCase.expected_precachexia),
      true,
      `${clinicalCase.id}: provisional early-risk pattern`
    );
  }
});

test("browser risk arithmetic matches the documented simulation case", () => {
  const clinicalCase = clinicalCases.risk_case;
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
    const result = calculator.risk(caseInput, derived, horizon);
    const expected = clinicalCase.expected[horizon];
    assert.ok(Math.abs(result.probability - expected.probability) < 1e-12);
    assert.equal(result.band, expected.band);
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
      result.fearon.startsWith(clinicalCase.expected_cachexia),
      true,
      `${clinicalCase.case_id}: cachexia`
    );
    assert.equal(
      result.pre.startsWith(clinicalCase.expected_early_risk),
      true,
      `${clinicalCase.case_id}: provisional early-risk pattern`
    );
  }
});
