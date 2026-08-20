"""Load the single versioned source of simulation assumptions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "simulation_assumptions.v1.json"
)


def load_simulation_config(
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    warning = config.get("metadata", {}).get("warning", "")
    if "simulation assumption" not in warning.lower():
        raise ValueError("Configuration must explicitly label simulation assumptions.")
    return config
