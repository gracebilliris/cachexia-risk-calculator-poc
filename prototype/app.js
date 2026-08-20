"use strict";

// Generated simulation-config.js is the executable source shared with Python.
const CONFIG = window.SIMULATION_CONFIG;
if (!CONFIG) throw new Error("Missing generated simulation configuration.");
const calculator = window.CachexiaCalculations.createCalculator(CONFIG);

const $ = (id) => document.getElementById(id);
const weightContainer = $("weights");

function addWeightRow(dateValue = "", weightValue = "") {
  const row = document.createElement("div");
  row.className = "weight-row";
  row.innerHTML = `
    <label>Measurement date *<input class="weight-date" type="date" value="${dateValue}"></label>
    <label>Weight (kg, 25–160) *<input class="weight-value" type="number" min="25" max="160" step="0.1" value="${weightValue}"></label>
    <button type="button" class="remove-weight" aria-label="Remove weight">Remove</button>`;
  row.querySelector(".remove-weight").addEventListener("click", () => row.remove());
  weightContainer.appendChild(row);
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
  if (!predictionDate) errors.push("Enter a prediction date.");
  if (!Number.isInteger(age) || age < ageBounds.minimum || age > ageBounds.maximum) errors.push(`Age must be a whole number from ${ageBounds.minimum} through ${ageBounds.maximum}.`);
  if (height !== null && (!Number.isFinite(height) || height < heightMinimum || height > heightMaximum)) errors.push(`Height must be ${heightMinimum}–${heightMaximum} cm or left unknown.`);
  const weights = [...document.querySelectorAll(".weight-row")].map((row, index) => {
    const date = row.querySelector(".weight-date").value;
    const value = Number(row.querySelector(".weight-value").value);
    if (!date) errors.push(`Weight row ${index + 1}: enter a date.`);
    if (!Number.isFinite(value) || value < weightBounds.minimum || value > weightBounds.maximum) errors.push(`Weight row ${index + 1}: weight must be ${weightBounds.minimum}–${weightBounds.maximum} kg.`);
    return { date, weightKg: value, index };
  });
  if (!weights.length) errors.push("Add at least one weight measurement.");
  return {
    errors, predictionDate, age, height, weights,
    stage: $("stage").value, ecog: $("ecog").value,
    appetite: $("appetite").value, sarcopenia: $("sarcopenia").value,
    cancerType: $("cancer-type").value
  };
}

function showMetric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function showRisk(result, suffix) {
  $(`risk-${suffix}`).textContent = result.probability === null
    ? "withheld"
    : `${(result.probability * 100).toFixed(1)}%`;
  $(`band-${suffix}`).textContent = result.probability === null
    ? "UNKNOWN — required baseline predictors are unavailable"
    : `${result.band.toUpperCase()} simulated band — not a calibrated probability`;
  $(`factors-${suffix}`).innerHTML = result.factors.map((factor) => `<li>${factor}</li>`).join("");
}

function clearOutputs() {
  $("derived").innerHTML = showMetric("Status", "not calculated");
  $("fearon").textContent = "Not calculated";
  $("precachexia").textContent = "Not calculated";
  for (const suffix of ["3m", "6m"]) {
    $(`risk-${suffix}`).textContent = "—";
    $(`band-${suffix}`).textContent = "Not calculated";
    $(`factors-${suffix}`).innerHTML = "";
  }
}

function calculate() {
  clearOutputs();
  const input = readInput();
  $("errors").innerHTML = input.errors.length ? `<ul>${input.errors.map((error) => `<li>${error}</li>`).join("")}</ul>` : "";
  if (input.errors.length) return;
  const derived = calculator.calculateDerived(input);
  if (!derived.baseline) {
    $("errors").textContent = "No weight exists on or before the prediction date. Add an eligible measurement.";
    return;
  }
  const format = (value, digits = 2) => value === null ? "not calculable" : value.toFixed(digits);
  $("derived").innerHTML =
    showMetric("Baseline weight", `${derived.baseline.weightKg.toFixed(1)} kg (${derived.baseline.date})`) +
    showMetric("Prior weight", derived.prior ? `${derived.prior.weightKg.toFixed(1)} kg (${derived.prior.date})` : "not calculable") +
    showMetric("BMI", derived.bmi === null ? "unknown" : `${format(derived.bmi)} kg/m²`) +
    showMetric("Weight loss", derived.loss === null ? "not calculable" : `${format(derived.loss)}%`) +
    showMetric("Interval", derived.days === null ? "not calculable" : `${derived.days} days`) +
    showMetric("Rate", derived.kgRate === null ? "not calculable" : `${format(derived.kgRate)} kg/month`) +
    showMetric("Percentage rate", derived.percentRate === null ? "not calculable" : `${format(derived.percentRate)} pp/month`) +
    showMetric("Trajectory", derived.trajectory);
  const labels = calculator.classify(input, derived);
  $("fearon").textContent = labels.fearon;
  $("precachexia").textContent = labels.pre;
  showRisk(calculator.risk(input, derived, "three_month"), "3m");
  showRisk(calculator.risk(input, derived, "six_month"), "6m");
}

$("add-weight").addEventListener("click", () => addWeightRow());
$("calculate").addEventListener("click", calculate);
addWeightRow("2025-07-31", "80");
addWeightRow("2026-01-31", "76");
calculate();
