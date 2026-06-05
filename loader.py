"""Data loading and validation helpers — no Streamlit dependency.

Called by app.py at startup. Extracted here so the logic is testable
without a running Streamlit server.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from core.models import AlertRecord, ScenarioMeta, ScenarioPayload

DATA_DIR = Path("data/scenarios")
METADATA_PATH = DATA_DIR / "metadata.json"
SCENARIOS_DIR = Path("config/scenarios")


def load_metadata(metadata_path: Path = METADATA_PATH) -> dict:
    """Load and return the parsed metadata.json dict."""
    return json.loads(metadata_path.read_text())


def validate_data_exists(
    metadata: dict,
    data_dir: Path = DATA_DIR,
) -> list[str]:
    """Check that all parquet and alert JSON files referenced in metadata exist.

    Returns:
        List of missing file path strings. Empty list means all data is present.
    """
    missing: list[str] = []
    for entry in metadata.get("scenarios", []):
        parquet_rel = entry.get("parquet_path", "")
        alerts_rel = entry.get("alerts_path", "")
        parquet_abs = data_dir.parent / parquet_rel
        alerts_abs = data_dir.parent / alerts_rel
        if not parquet_abs.exists():
            missing.append(str(parquet_abs))
        if not alerts_abs.exists():
            missing.append(str(alerts_abs))
    return missing


def _load_alerts(alerts_path: Path) -> list[AlertRecord]:
    """Load alert records from a JSON file."""
    raw = json.loads(alerts_path.read_text())
    return [
        AlertRecord(
            tick=a["tick"],
            facility_id=a["facility_id"],
            network_id=a["network_id"],
            alert_type=a["alert_type"],
            message=a["message"],
            shap_contributions=a.get("shap_contributions", {}),
            severity=a.get("severity", "info"),
        )
        for a in raw
    ]


def load_scenario_payloads(
    metadata_path: Path = METADATA_PATH,
    data_dir: Path = DATA_DIR,
) -> dict[str, ScenarioPayload]:
    """Load all scenario parquets and alert JSONs into ScenarioPayload dicts.

    Args:
        metadata_path: Path to metadata.json.
        data_dir: Base directory for scenario data files.

    Returns:
        Dict mapping scenario_id to ScenarioPayload (tick_df, alerts, metadata).

    Raises:
        FileNotFoundError: If metadata.json or any referenced data file is missing.
    """
    metadata = load_metadata(metadata_path)
    payloads: dict[str, Any] = {}

    for entry in metadata["scenarios"]:
        sc_id = entry["id"]
        parquet_path = data_dir.parent / entry["parquet_path"]
        alerts_path = data_dir.parent / entry["alerts_path"]

        tick_df = pd.read_parquet(parquet_path)
        alerts = _load_alerts(alerts_path)

        # Load reroutes and recommended_actions from scenario YAML (optional)
        reroutes: list[list] = []
        recommended_actions: dict[str, list[str]] = {}
        yaml_path = SCENARIOS_DIR / f"{sc_id}.yaml"
        if yaml_path.exists():
            sc_yaml = yaml.safe_load(yaml_path.read_text())
            reroutes = [list(r) for r in sc_yaml.get("reroutes", [])]
            recommended_actions = {
                fac: list(actions)
                for fac, actions in sc_yaml.get("recommended_actions", {}).items()
            }

        primary_network = sc_yaml.get("primary_network", "NET-A") if yaml_path.exists() else "NET-A"
        # SC-08 primary_network is "ALL" — resolve to first real network
        if str(primary_network).upper() in ("ALL", "ALL NETWORKS"):
            primary_network = "NET-A"

        scenario_meta: ScenarioMeta = {
            "id": entry["id"],
            "display_name": entry["display_name"],
            "tick_count": entry["tick_count"],
            "network_ids": entry["network_ids"],
            "primary_network": str(primary_network),
            "parquet_path": entry["parquet_path"],
            "alerts_path": entry["alerts_path"],
            "reroutes": reroutes,
            "recommended_actions": recommended_actions,
        }

        payloads[sc_id] = ScenarioPayload(
            tick_df=tick_df,
            alerts=alerts,
            metadata=scenario_meta,
        )

    return payloads
