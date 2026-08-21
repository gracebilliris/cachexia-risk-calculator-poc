#!/usr/bin/env python3
"""Generate versioned synthetic sample data and a distribution summary."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cachexia_poc.generator import generate_patients, write_csv, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260820)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    patients = generate_patients(args.count, args.seed)
    write_json(patients, args.output_dir / "synthetic_patients.v1.json")
    write_csv(patients, args.output_dir / "synthetic_patients.v1.csv")
    summary = {
        "warning": "Synthetic simulation output; not clinically validated or for medical use.",
        "count": len(patients),
        "seed": args.seed,
        "config_version": patients[0]["provenance"]["config_version"],
        "sex": Counter(patient["sex"] for patient in patients),
        "cancer_type": Counter(patient["cancer_type"] for patient in patients),
        "stage": Counter(patient["cancer_stage"] for patient in patients),
        "ecog": Counter(
            "unknown" if patient["ecog"] is None else str(patient["ecog"])
            for patient in patients
        ),
        "appetite": Counter(patient["reduced_appetite"] for patient in patients),
        "baseline_cachexia_criteria_status": Counter(
            patient["baseline_criteria_status"]["cachexia_criteria_status"]
            for patient in patients
        ),
        "baseline_provisional_early_risk_candidate_status": Counter(
            patient["baseline_criteria_status"]["precachexia_candidate_status"]
            for patient in patients
        ),
        "illustrative_simulation_category_3m": Counter(
            patient["illustrative_simulation_3m"]["category"] or "withheld"
            for patient in patients
        ),
        "illustrative_simulation_category_6m": Counter(
            patient["illustrative_simulation_6m"]["category"] or "withheld"
            for patient in patients
        ),
        "outcome_3m_threshold_based_cachexia_status": Counter(
            patient["outcome_3m"]["threshold_based_cachexia_status"]
            for patient in patients
        ),
        "outcome_6m_threshold_based_cachexia_status": Counter(
            patient["outcome_6m"]["threshold_based_cachexia_status"]
            for patient in patients
        ),
        "edge_cases": Counter(
            patient["edge_case"] or "none" for patient in patients
        ),
    }
    with (args.output_dir / "distribution_summary.v1.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    print(
        f"Generated {len(patients)} synthetic patients with seed {args.seed} "
        f"in {args.output_dir}"
    )


if __name__ == "__main__":
    main()
