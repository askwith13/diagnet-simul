"""Scenario and network config loaders for the generation pipeline.

This module is build-time only. It MUST NOT be imported by app.py, viz/, or tabs/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

NETWORKS_PATH = Path("config/networks.yaml")
SCENARIOS_DIR = Path("config/scenarios")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class AlertConfig:
    """One scripted alert entry from a scenario YAML."""
    tick: int
    type: str         # critical | dto_advisory | bayesian | recommendation | warning
    severity: str     # critical | high | medium | low | info
    recipient: str
    facility: str     # facility_id the alert fires for
    msg: str          # format template string


@dataclass
class ScenarioConfig:
    """Fully-parsed scenario YAML as a typed Python object."""
    scenario_id: str                                    # stem of the YAML file (e.g. "sc-01")
    name: str
    primary_network: str
    max_ticks: int
    affected_facilities: list[str]
    per_tick_deltas: dict[str, dict[str, float]]        # facility_id -> {field: delta}
    shap_weights: dict[str, float]                      # field_name -> weight
    reroutes: list[list[str]]                           # [[from, to], ...]
    alerts: list[AlertConfig]
    recommended_actions: dict[str, list[str]]           # facility_id -> [action, ...]
    initial_states: Optional[dict[str, dict[str, dict[str, float]]]] = None  # SC-08
    impact_metrics: Optional[list[str]] = None          # SC-08
    event_activation_tick: Optional[int] = None         # tick at which post_event_deltas activate
    post_event_deltas: Optional[dict[str, dict[str, float]]] = None  # recovery deltas after event


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_networks_yaml(path: Path = NETWORKS_PATH) -> dict[str, set[str]]:
    """Load networks.yaml and return {network_id: set_of_facility_ids}.

    Returns:
        Dict mapping each network ID to the set of facility IDs it contains.
    """
    data = yaml.safe_load(path.read_text())
    return {
        net_id: set(net["facilities"].keys())
        for net_id, net in data["networks"].items()
    }


def all_facility_ids(networks: dict[str, set[str]]) -> set[str]:
    """Flatten network->facility mapping to a single set of all facility IDs."""
    return {fid for fids in networks.values() for fid in fids}


def load_scenario_yaml(path: str | Path, scenario_id: str | None = None) -> ScenarioConfig:
    """Load a single scenario YAML file into a ScenarioConfig.

    Args:
        path: Path to the scenario YAML file.
        scenario_id: Override the scenario ID. Defaults to the file stem.

    Returns:
        A fully-populated ScenarioConfig dataclass.
    """
    path = Path(path)
    sid = scenario_id or path.stem
    data = yaml.safe_load(path.read_text())

    alerts = [
        AlertConfig(
            tick=a["tick"],
            type=a["type"],
            severity=a.get("severity", "info"),
            recipient=a["recipient"],
            facility=a["facility"],
            msg=a["msg"],
        )
        for a in data.get("alerts", [])
    ]

    return ScenarioConfig(
        scenario_id=sid,
        name=data["name"],
        primary_network=data["primary_network"],
        max_ticks=data["max_ticks"],
        affected_facilities=list(data.get("affected_facilities", [])),
        per_tick_deltas={
            fac: dict(deltas)
            for fac, deltas in data.get("per_tick_deltas", {}).items()
        },
        shap_weights=dict(data.get("shap_weights", {})),
        reroutes=[list(r) for r in data.get("reroutes", [])],
        alerts=alerts,
        recommended_actions={
            fac: list(actions)
            for fac, actions in data.get("recommended_actions", {}).items()
        },
        initial_states=data.get("initial_states"),
        impact_metrics=data.get("impact_metrics"),
        event_activation_tick=data.get("event_activation_tick"),
        post_event_deltas={
            fac: dict(deltas)
            for fac, deltas in data.get("post_event_deltas", {}).items()
        } if data.get("post_event_deltas") else None,
    )


def load_all_scenarios(scenarios_dir: Path = SCENARIOS_DIR) -> dict[str, ScenarioConfig]:
    """Load all scenario YAML files from scenarios_dir.

    Returns:
        Dict mapping scenario_id to ScenarioConfig, sorted by scenario_id.
    """
    configs: dict[str, ScenarioConfig] = {}
    for path in sorted(scenarios_dir.glob("*.yaml")):
        config = load_scenario_yaml(path)
        configs[config.scenario_id] = config
    return configs


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config(config: ScenarioConfig, known_facility_ids: set[str]) -> None:
    """Validate a ScenarioConfig against the set of known facility IDs.

    Checks:
    1. All affected_facilities exist in networks.yaml.
    2. All per_tick_deltas facility IDs exist in networks.yaml.
    3. All shap_weights keys cover every field in per_tick_deltas.

    Raises:
        ValueError: With a descriptive message naming the offending value.
    """
    # 1. Check affected_facilities
    for fid in config.affected_facilities:
        if fid not in known_facility_ids:
            raise ValueError(
                f"Unknown facility '{fid}' in affected_facilities of scenario "
                f"'{config.name}' — not found in networks.yaml"
            )

    # 2. Check per_tick_deltas facility IDs
    for fid in config.per_tick_deltas:
        if fid not in known_facility_ids:
            raise ValueError(
                f"Unknown facility '{fid}' in per_tick_deltas of scenario "
                f"'{config.name}' — not found in networks.yaml"
            )

    # 3. Check shap_weights cover all delta fields
    all_delta_fields: set[str] = {
        field_name
        for deltas in config.per_tick_deltas.values()
        for field_name in deltas
    }
    missing_weights = all_delta_fields - set(config.shap_weights.keys())
    if missing_weights:
        raise ValueError(
            f"Scenario '{config.name}': shap_weights missing entries for "
            f"per_tick_delta fields: {sorted(missing_weights)}"
        )
