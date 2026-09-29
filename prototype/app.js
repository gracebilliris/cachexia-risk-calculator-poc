"use strict";

const CONFIG = window.SIMULATION_CONFIG;
if (!CONFIG) throw new Error("Missing generated simulation configuration.");
const calculator = window.CachexiaCalculations.createCalculator(CONFIG);

const $ = (id) => document.getElementById(id);
const weightContainer = $("weights");

function syncCancerSubtype() {
  const subtype = $("cancer-subtype");
  const field = $("lung-subtype-field");
  const previous = subtype.value;
  const isLung = $("cancer-type").value === "lung";
  const values = window.CachexiaCalculations.cancerSubtypeOptions(
    $("cancer-type").value
  );
  subtype.replaceChildren(...values.map((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    return option;
  }));
  subtype.value = values.includes(previous)
    ? previous
    : (isLung ? "unknown" : "not applicable");
  subtype.disabled = !isLung;
  field.hidden = !isLung;
}

function addWeightRow(dateValue = "", weightValue = "", markAsChanged = false) {
  const row = document.createElement("div");
  row.className = "weight-row";
  row.innerHTML = `
    <label>Measurement date *<input class="weight-date" type="date" value="${dateValue}"></label>
    <label>Weight (kg, 25–160) *<input class="weight-value" type="number" min="25" max="160" step="0.1" value="${weightValue}"></label>
    <button type="button" class="remove-weight" aria-label="Remove weight">Remove</button>`;
  row.querySelector(".remove-weight").addEventListener("click", () => {
    row.remove();
    markDirty();
  });
  weightContainer.appendChild(row);
  if (markAsChanged) markDirty();
}

function readInput() {
  const errors = [];
  const predictionDate = $("prediction-date").value;
  const age = Number($("age").value);
  const heightText = $("height").value;
  const height = heightText === "" ? null : Number(heightText);
  const ageBounds = CONFIG.cohort.age;
  const heightValues = Object.values(CONFIG.cohort.height_cm);
  const heightMinimum = Math.min(...heightValues.map((item) => item.minimum));
  const heightMaximum = Math.max(...heightValues.map((item) => item.maximum));
  const weightBounds = CONFIG.cohort.historical_weight_kg;
  if (!predictionDate) errors.push("Enter an assessment date.");
  if (!Number.isInteger(age) || age < ageBounds.minimum || age > ageBounds.maximum) errors.push(`Age must be a whole number from ${ageBounds.minimum} through ${ageBounds.maximum}.`);
  if (height === null) errors.push("Enter height to calculate BMI.");
  else if (!Number.isFinite(height) || height < heightMinimum || height > heightMaximum) errors.push(`Height must be ${heightMinimum}–${heightMaximum} cm.`);
  const weights = [...document.querySelectorAll(".weight-row")].map((row, index) => {
    const date = row.querySelector(".weight-date").value;
    const value = Number(row.querySelector(".weight-value").value);
    if (!date) errors.push(`Weight row ${index + 1}: enter a date.`);
    if (!Number.isFinite(value) || value < weightBounds.minimum || value > weightBounds.maximum) errors.push(`Weight row ${index + 1}: weight must be ${weightBounds.minimum}–${weightBounds.maximum} kg.`);
    return { date, weightKg: value, index };
  });
  if (weights.length < 2) errors.push("Add at least two dated weight measurements.");
  return {
    errors, predictionDate, age, height, weights,
    stage: $("stage").value, ecog: $("ecog").value,
    appetite: $("appetite").value, sarcopenia: $("sarcopenia").value,
    activeCancer: $("active-cancer").value === "yes",
    sex: $("sex").value,
    cancerType: $("cancer-type").value,
    cancerSubtype: $("cancer-subtype").value
  };
}

function showMetric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function showCategory(result, suffix) {
  $(`category-${suffix}`).textContent = result.category === null
    ? "Not available"
    : result.category;
  $(`basis-${suffix}`).textContent = result.category === null
    ? "Complete the required information and confirm eligibility to display this category."
    : `Illustrative ${result.horizonMonths}-month category using baseline synthetic information. This is not a probability.`;
  $(`factors-${suffix}`).innerHTML = result.explanations
    .map((explanation) => `<li>${explanation}</li>`)
    .join("");
}

function clearOutputs() {
  $("derived").innerHTML = showMetric("Status", "not calculated");
  $("fearon").textContent = "Not calculated";
  $("precachexia").textContent = "Not calculated";
  $("clinical-state").textContent = "Not calculated";
  $("clinical-message").textContent = "Complete the required fields and calculate the results.";
  $("eligibility").textContent = "Not calculated";
  for (const suffix of ["3m", "6m"]) {
    $(`category-${suffix}`).textContent = "—";
    $(`basis-${suffix}`).textContent = "Not calculated";
    $(`factors-${suffix}`).innerHTML = "";
  }
}

function markDirty() {
  clearOutputs();
  $("errors").replaceChildren();
  $("calculation-status").textContent = "Inputs changed. Select Calculate results to update the outputs.";
}

function calculate({ revealResults = false } = {}) {
  clearOutputs();
  const input = readInput();
  $("errors").innerHTML = input.errors.length ? `<ul>${input.errors.map((error) => `<li>${error}</li>`).join("")}</ul>` : "";
  if (input.errors.length) {
    $("calculation-status").textContent = "Please correct the fields listed below.";
    return;
  }
  const derived = calculator.calculateDerived(input);
  if (!derived.baseline) {
    $("errors").textContent = "No weight exists on or before the assessment date. Add an eligible measurement.";
    $("calculation-status").textContent = "Please add a weight on or before the assessment date.";
    return;
  }
  const format = (value, digits = 2) => value === null ? "not calculable" : value.toFixed(digits);
  const weightChange = derived.loss === null
    ? "Not calculable"
    : derived.loss > 0
      ? `${format(derived.loss, 1)}% loss`
      : derived.loss < 0
        ? `${format(Math.abs(derived.loss), 1)}% gain`
        : "No change";
  $("derived").innerHTML =
    showMetric("Assessment weight", `${derived.baseline.weightKg.toFixed(1)} kg`) +
    showMetric("Earlier weight", derived.prior ? `${derived.prior.weightKg.toFixed(1)} kg` : "Not calculable") +
    showMetric("BMI", derived.bmi === null ? "Unknown" : format(derived.bmi, 1)) +
    showMetric("Weight change", weightChange) +
    showMetric("Measurement interval", derived.days === null ? "Not calculable" : `${derived.days} days`) +
    showMetric("Weight trajectory", derived.trajectory);
  const labels = calculator.classify(input, derived);
  const plainStatus = (status) => status.startsWith("yes")
    ? "Yes"
    : status.startsWith("no")
      ? "No"
      : "Unable to determine";
  $("fearon").textContent = plainStatus(labels.cachexiaCriteria);
  $("precachexia").textContent = plainStatus(labels.precachexiaCandidate);
  $("clinical-state").textContent = labels.clinicalState;
  $("clinical-message").textContent = labels.clinicalState === "Cachexia"
    ? "The synthetic measurements meet the current operational cachexia rule."
    : labels.clinicalState === "Pre-cachexia"
      ? "The synthetic measurements meet the provisional pre-cachexia rule."
      : labels.clinicalState === "No cachexia"
        ? "The synthetic measurements do not meet either current operational rule."
        : "More information is needed before a classification can be shown.";
  const category3 = calculator.category(input, derived, "three_month");
  const category6 = calculator.category(input, derived, "six_month");
  const reasons = category3.withholdingReasons || [];
  $("eligibility").textContent = labels.clinicalState === "Cachexia"
    ? "No—cachexia at assessment"
    : labels.cachexiaCriteria.startsWith("unknown")
      ? "Not yet—more information needed"
      : reasons.includes("cancer_not_active") || reasons.includes("stage_not_I_to_IV")
        ? "No—outside the target population"
        : "Yes";
  showCategory(category3, "3m");
  showCategory(category6, "6m");
  $("calculation-status").textContent = "Results updated using the synthetic information entered above.";
  if (revealResults) {
    $("results-heading").focus({ preventScroll: true });
    $("results-heading").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function clearWeights() {
  weightContainer.replaceChildren();
}

function setProfile(profile, shouldScroll = true) {
  $("prediction-date").value = profile.predictionDate;
  $("age").value = profile.age;
  $("sex").value = profile.sex;
  $("active-cancer").value = profile.activeCancer;
  $("cancer-type").value = profile.cancerType;
  syncCancerSubtype();
  $("cancer-subtype").value = profile.cancerSubtype;
  $("stage").value = profile.stage;
  $("height").value = profile.height;
  $("ecog").value = profile.ecog;
  $("appetite").value = profile.appetite;
  $("sarcopenia").value = "unknown";
  clearWeights();
  profile.weights.forEach(([dateValue, weightValue]) => addWeightRow(dateValue, weightValue));
  calculate();
  if (shouldScroll) {
    $("calculator").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

const defaultProfile = {
  predictionDate: "2026-01-31", age: 65, sex: "female", activeCancer: "yes",
  cancerType: "lung", cancerSubtype: "NSCLC", stage: "III", height: 170,
  ecog: "2", appetite: "no", weights: [["2025-07-31", "80"], ["2026-01-31", "76"]]
};
const lowerProfile = {
  predictionDate: "2026-01-31", age: 48, sex: "female", activeCancer: "yes",
  cancerType: "breast", cancerSubtype: "not applicable", stage: "I", height: 164,
  ecog: "0", appetite: "no", weights: [["2025-07-31", "66"], ["2026-01-31", "65.5"]]
};
const higherProfile = {
  predictionDate: "2026-01-31", age: 72, sex: "male", activeCancer: "yes",
  cancerType: "pancreatic", cancerSubtype: "not applicable", stage: "IV", height: 176,
  ecog: "3", appetite: "yes", weights: [["2025-07-31", "74"], ["2026-01-31", "72"]]
};

$("add-weight").addEventListener("click", () => addWeightRow("", "", true));
$("calculate").addEventListener("click", () => calculate({ revealResults: true }));
$("cancer-type").addEventListener("change", syncCancerSubtype);
$("load-lower").addEventListener("click", () => setProfile(lowerProfile));
$("load-higher").addEventListener("click", () => setProfile(higherProfile));
$("reset").addEventListener("click", () => setProfile(defaultProfile));
$("calculator").addEventListener("input", markDirty);
$("calculator").addEventListener("change", markDirty);
setProfile(defaultProfile, false);
