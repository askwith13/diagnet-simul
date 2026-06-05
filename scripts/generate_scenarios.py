#!/usr/bin/env python3
"""Generate pre-computed scenario data for the DiagNet simulation platform.

Outputs (per scenario):
    data/scenarios/<id>.parquet          — tick history (FlatTickSnapshot rows)
    data/scenarios/<id>_alerts.json      — fired alert records with SHAP
    data/scenarios/metadata.json         — scenario registry loaded at app startup

Usage:
    uv run python scripts/generate_scenarios.py --all [--validate] [--force]
    uv run python scripts/generate_scenarios.py --scenario SC-01 [--validate]
    uv run python scripts/generate_scenarios.py --validate   # validate only, no output

MUST be run from the project root directory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import fields
from pathlib import Path

import pandas as pd
import yaml

# Ensure project root is on path when run directly
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from core.models import FacilityState
from generation.engine import ScenarioGenerator
from generation.scenario_config import (
    ScenarioConfig,
    all_facility_ids,
    load_all_scenarios,
    load_networks_yaml,
    validate_config,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_DIR = _ROOT / "data" / "scenarios"
SCHEMA_VERSION = "1.0.0"
DEFAULT_SEED = 42
FACILITY_FIELD_NAMES = {f.name for f in fields(FacilityState)}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_alert_tokens(config: ScenarioConfig) -> list[str]:
    """Return error strings for alert msg tokens that aren't FacilityState fields."""
    errors: list[str] = []
    for alert in config.alerts:
        tokens = {
            m.group(1)
            for m in re.finditer(r"\{(\w+)(?:[^}]*)?\}", alert.msg)
        }
        for token in tokens:
            if token not in FACILITY_FIELD_NAMES:
                errors.append(
                    f"Scenario '{config.name}' tick {alert.tick}: "
                    f"alert msg references unknown FacilityState field '{token}'"
                )
    return errors


def run_validation(scenarios: dict[str, ScenarioConfig], known_ids: set[str]) -> int:
    """Run all validations. Returns 0 on success, 1 on any error."""
    all_errors: list[str] = []

    for sc_id, config in scenarios.items():
        # Facility ID + shap_weights checks
        try:
            validate_config(config, known_ids)
        except ValueError as exc:
            all_errors.append(str(exc))

        # Alert token checks
        all_errors.extend(_validate_alert_tokens(config))

    if all_errors:
        print("VALIDATION FAILED:", file=sys.stderr)
        for err in all_errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1

    print(f"  ✓ All {len(scenarios)} scenarios valid")
    return 0


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def _scenario_entry(config: ScenarioConfig, network_ids: list[str]) -> dict:
    sc_id = config.scenario_id
    return {
        "id": sc_id,
        "display_name": config.name,
        "tick_count": config.max_ticks,
        "network_ids": network_ids,
        "parquet_path": f"scenarios/{sc_id}.parquet",
        "alerts_path": f"scenarios/{sc_id}_alerts.json",
    }


def generate_one(
    config: ScenarioConfig,
    networks_data: dict,
    output_dir: Path,
    seed: int,
    force: bool,
) -> dict:
    """Generate parquet + alerts JSON for one scenario. Returns metadata entry."""
    sc_id = config.scenario_id
    parquet_path = output_dir / f"{sc_id}.parquet"
    alerts_path = output_dir / f"{sc_id}_alerts.json"
    network_ids = list(networks_data["networks"].keys())

    if parquet_path.exists() and not force:
        print(f"  [{sc_id}] already exists — skipping (use --force to overwrite)")
        return _scenario_entry(config, network_ids)

    print(f"  [{sc_id}] {config.name} ({config.max_ticks} ticks × 59 facilities)...",
          end=" ", flush=True)
    t0 = time.perf_counter()

    gen = ScenarioGenerator(config, networks_data, seed=seed)
    snapshots, alerts = gen.run_with_alerts()

    # --- Parquet ---
    df = pd.DataFrame(snapshots)
    # Optimise storage dtypes
    df["tick"] = df["tick"].astype("int16")
    df["facility_id"] = df["facility_id"].astype("category")
    df["network_id"] = df["network_id"].astype("category")
    for col in df.select_dtypes(include="float64").columns:
        df[col] = df[col].astype("float32")

    df.to_parquet(parquet_path, engine="pyarrow", compression="snappy", index=False)

    # --- Alerts JSON ---
    alerts_data = [
        {
            "tick": a.tick,
            "facility_id": a.facility_id,
            "network_id": a.network_id,
            "alert_type": a.alert_type,
            "message": a.message,
            "shap_contributions": {k: float(v) for k, v in a.shap_contributions.items()},
            "severity": a.severity,
        }
        for a in alerts
    ]
    alerts_path.write_text(json.dumps(alerts_data, indent=2))

    elapsed = time.perf_counter() - t0
    kb = parquet_path.stat().st_size / 1024
    print(f"{len(snapshots)} rows · {df.shape[1]} cols · {kb:.1f} KB · {elapsed:.1f}s")

    return _scenario_entry(config, network_ids)


def update_metadata(output_dir: Path, entries: list[dict]) -> None:
    """Write or merge entries into metadata.json."""
    meta_path = output_dir / "metadata.json"
    existing: dict[str, dict] = {}

    if meta_path.exists():
        data = json.loads(meta_path.read_text())
        existing = {e["id"]: e for e in data.get("scenarios", [])}

    for entry in entries:
        existing[entry["id"]] = entry

    meta_path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "scenarios": sorted(existing.values(), key=lambda e: e["id"]),
            },
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate DiagNet pre-computed scenario data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="Generate all 8 scenarios")
    group.add_argument(
        "--scenario", metavar="SC_ID",
        help="Generate one scenario by ID (e.g. SC-01 or sc-01)",
    )
    parser.add_argument("--validate", action="store_true",
                        help="Validate YAML configs before generating")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing parquet/JSON outputs")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help=f"Output directory (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    if not args.all and args.scenario is None and not args.validate:
        parser.error("Specify --all, --scenario SC-ID, or --validate")

    # --- Load configs ---
    print("Loading configs...")
    networks_data = yaml.safe_load((Path("config/networks.yaml")).read_text())
    all_scenarios = load_all_scenarios()
    known_ids = all_facility_ids(load_networks_yaml())

    # --- Select target scenarios ---
    if args.all:
        target_scenarios = all_scenarios
    elif args.scenario:
        sc_key = args.scenario.lower()
        if sc_key not in all_scenarios:
            print(f"ERROR: scenario '{args.scenario}' not found. "
                  f"Available: {sorted(all_scenarios.keys())}", file=sys.stderr)
            return 1
        target_scenarios = {sc_key: all_scenarios[sc_key]}
    else:
        target_scenarios = all_scenarios  # validate-only touches all

    # --- Validate ---
    if args.validate:
        print("Validating scenarios...")
        rc = run_validation(target_scenarios, known_ids)
        if rc != 0:
            return rc

    if not args.all and args.scenario is None:
        # validate-only mode: done
        return 0

    # --- Generate ---
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nGenerating {len(target_scenarios)} scenario(s) → {args.output_dir}")

    entries: list[dict] = []
    for sc_id in sorted(target_scenarios.keys()):
        config = target_scenarios[sc_id]
        entry = generate_one(config, networks_data, args.output_dir, args.seed, args.force)
        entries.append(entry)

    update_metadata(args.output_dir, entries)
    meta_path = args.output_dir / "metadata.json"
    meta = json.loads(meta_path.read_text())
    total_kb = sum(
        (args.output_dir / f"{e['id']}.parquet").stat().st_size / 1024
        for e in meta["scenarios"]
        if (args.output_dir / f"{e['id']}.parquet").exists()
    )
    print(f"\nDone. metadata.json updated ({len(meta['scenarios'])} scenarios). "
          f"Total parquet: {total_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
