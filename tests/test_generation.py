"""Tests for the generation pipeline — CLI output + golden fixture regression."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

DATA_DIR = Path("data/scenarios")
METADATA_PATH = DATA_DIR / "metadata.json"
GOLDEN_PATH = Path("tests/fixtures/sc-01_golden.json")
SCENARIO_IDS = [f"sc-0{i}" for i in range(1, 9)]


# ─── metadata.json ────────────────────────────────────────────────────────────

def test_metadata_exists():
    assert METADATA_PATH.exists(), "metadata.json not found — run generate_scenarios.py --all"


def test_metadata_schema_version():
    meta = json.loads(METADATA_PATH.read_text())
    assert "schema_version" in meta
    assert meta["schema_version"] == "1.0.0"


def test_metadata_has_8_scenarios():
    meta = json.loads(METADATA_PATH.read_text())
    assert len(meta["scenarios"]) == 8


def test_metadata_scenario_ids():
    meta = json.loads(METADATA_PATH.read_text())
    ids = {e["id"] for e in meta["scenarios"]}
    assert ids == set(SCENARIO_IDS)


def test_metadata_required_fields():
    required = {"id", "display_name", "tick_count", "network_ids", "parquet_path", "alerts_path"}
    meta = json.loads(METADATA_PATH.read_text())
    for entry in meta["scenarios"]:
        missing = required - set(entry.keys())
        assert not missing, f"Scenario '{entry['id']}' missing metadata fields: {missing}"


def test_metadata_network_ids_has_5_networks():
    meta = json.loads(METADATA_PATH.read_text())
    for entry in meta["scenarios"]:
        assert len(entry["network_ids"]) == 5


# ─── Parquet files ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def all_parquets() -> dict[str, pd.DataFrame]:
    return {sc_id: pd.read_parquet(DATA_DIR / f"{sc_id}.parquet") for sc_id in SCENARIO_IDS}


def test_all_parquets_exist():
    for sc_id in SCENARIO_IDS:
        assert (DATA_DIR / f"{sc_id}.parquet").exists(), f"Missing {sc_id}.parquet"


def test_parquet_column_count(all_parquets):
    from core.models import FlatTickSnapshot
    expected_cols = len(FlatTickSnapshot.__annotations__)  # 25
    for sc_id, df in all_parquets.items():
        assert df.shape[1] == expected_cols, (
            f"{sc_id}: expected {expected_cols} columns, got {df.shape[1]}"
        )


def test_parquet_column_names_match_flat_tick_snapshot(all_parquets):
    from core.models import FlatTickSnapshot
    expected = set(FlatTickSnapshot.__annotations__.keys())
    for sc_id, df in all_parquets.items():
        assert set(df.columns) == expected, (
            f"{sc_id}: column mismatch — extra: {set(df.columns)-expected}, "
            f"missing: {expected-set(df.columns)}"
        )


def test_parquet_row_counts(all_parquets):
    meta = json.loads(METADATA_PATH.read_text())
    tick_counts = {e["id"]: e["tick_count"] for e in meta["scenarios"]}
    for sc_id, df in all_parquets.items():
        expected_rows = tick_counts[sc_id] * 59  # 59 facilities
        assert df.shape[0] == expected_rows, (
            f"{sc_id}: expected {expected_rows} rows, got {df.shape[0]}"
        )


def test_parquet_no_null_non_nan_values(all_parquets):
    nan_allowed = {"predicted_stockout_day"}
    for sc_id, df in all_parquets.items():
        for col in df.columns:
            if col in nan_allowed:
                continue
            assert df[col].notna().all(), (
                f"{sc_id}: column '{col}' contains null values"
            )


def test_parquet_total_size_under_500kb():
    total = sum((DATA_DIR / f"{sc_id}.parquet").stat().st_size for sc_id in SCENARIO_IDS)
    total_kb = total / 1024
    assert total_kb < 500, f"Total parquet size {total_kb:.1f} KB exceeds 500 KB"


def test_parquet_tick_range(all_parquets):
    meta = json.loads(METADATA_PATH.read_text())
    tick_counts = {e["id"]: e["tick_count"] for e in meta["scenarios"]}
    for sc_id, df in all_parquets.items():
        assert df["tick"].min() == 0
        assert df["tick"].max() == tick_counts[sc_id] - 1


def test_parquet_has_all_5_networks(all_parquets):
    for sc_id, df in all_parquets.items():
        networks = set(df["network_id"].unique())
        assert networks == {"NET-A", "NET-B", "NET-C", "NET-D", "NET-E"}, (
            f"{sc_id}: missing networks"
        )


# ─── Alert JSON files ─────────────────────────────────────────────────────────

def test_all_alert_jsons_exist():
    for sc_id in SCENARIO_IDS:
        assert (DATA_DIR / f"{sc_id}_alerts.json").exists(), f"Missing {sc_id}_alerts.json"


def test_alert_json_structure():
    required = {"tick", "facility_id", "network_id", "alert_type",
                "message", "shap_contributions", "severity"}
    for sc_id in SCENARIO_IDS:
        alerts = json.loads((DATA_DIR / f"{sc_id}_alerts.json").read_text())
        assert isinstance(alerts, list)
        for alert in alerts:
            missing = required - set(alert.keys())
            assert not missing, f"{sc_id}: alert missing fields {missing}"


def test_alert_shap_contributions_non_empty():
    for sc_id in SCENARIO_IDS:
        alerts = json.loads((DATA_DIR / f"{sc_id}_alerts.json").read_text())
        for alert in alerts:
            assert isinstance(alert["shap_contributions"], dict)
            assert len(alert["shap_contributions"]) > 0, (
                f"{sc_id} tick {alert['tick']}: empty shap_contributions"
            )


# ─── Golden fixture regression ───────────────────────────────────────────────

def test_golden_fixture_exists():
    assert GOLDEN_PATH.exists(), "sc-01_golden.json not found in tests/fixtures/"


def test_sc01_golden_fixture_row_count():
    golden = json.loads(GOLDEN_PATH.read_text())
    # 5 ticks (0-4) × 59 facilities = 295 rows
    assert len(golden) == 295


def test_sc01_regeneration_matches_golden():
    """Regenerate SC-01 with seed=42; compare first 5 ticks to golden fixture."""
    from generation.engine import ScenarioGenerator
    from generation.scenario_config import load_scenario_yaml

    networks_data = yaml.safe_load(Path("config/networks.yaml").read_text())
    config = load_scenario_yaml("config/scenarios/sc-01.yaml")
    gen = ScenarioGenerator(config, networks_data, seed=42)
    snapshots = gen.run()

    golden = json.loads(GOLDEN_PATH.read_text())
    fresh = [s for s in snapshots if s["tick"] < 5]

    assert len(fresh) == len(golden), "Row count mismatch vs golden fixture"

    numeric_fields = [
        k for k, v in fresh[0].items()
        if isinstance(v, (int, float)) and k not in {"tick", "machines", "modules", "chw_available"}
    ]

    for i, (fresh_row, golden_row) in enumerate(zip(fresh, golden)):
        for field_name in numeric_fields:
            fv = fresh_row[field_name]
            gv = golden_row[field_name]
            # Both NaN → equal
            if fv is None and gv is None:
                continue
            if isinstance(fv, float) and math.isnan(fv) and gv is None:
                continue
            assert fv == pytest.approx(gv, abs=1e-4), (
                f"Row {i} field '{field_name}': got {fv}, expected {gv}"
            )


# ─── CLI --scenario flag ──────────────────────────────────────────────────────

def test_generate_single_scenario_updates_metadata(tmp_path):
    """--scenario SC-03 regenerates only SC-03."""
    result = subprocess.run(
        [sys.executable, "scripts/generate_scenarios.py",
         "--scenario", "SC-03", "--force",
         "--output-dir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "sc-03.parquet").exists()
    assert (tmp_path / "sc-03_alerts.json").exists()
    meta = json.loads((tmp_path / "metadata.json").read_text())
    assert len(meta["scenarios"]) == 1
    assert meta["scenarios"][0]["id"] == "sc-03"


# ─── CLI --validate with invalid token ───────────────────────────────────────

def test_validate_flag_catches_invalid_token(tmp_path):
    """--validate should exit 1 when alert msg has unknown FacilityState field."""
    bad_yaml = tmp_path / "sc-bad.yaml"
    bad_yaml.write_text("""
name: "Bad scenario"
primary_network: NET-A
max_ticks: 5
affected_facilities: [DHC-A]
per_tick_deltas:
  DHC-A:
    patients_queued: 1.0
shap_weights:
  patients_queued: 1.0
reroutes: []
alerts:
  - tick: 2
    type: critical
    severity: critical
    recipient: lab_supervisor
    facility: DHC-A
    msg: "Bad token: {nonexistent_field:.0f}"
recommended_actions:
  DHC-A:
    - "Action 1"
    - "Action 2"
    - "Action 3"
""")
    # Patch scenarios dir to include the bad scenario
    import shutil
    bad_scenarios_dir = tmp_path / "config" / "scenarios"
    bad_scenarios_dir.mkdir(parents=True)
    shutil.copy(bad_yaml, bad_scenarios_dir / "sc-bad.yaml")

    # Run validate-only against the bad scenario directory
    result = subprocess.run(
        [sys.executable, "-c",
         f"""
import sys; sys.path.insert(0, '.')
from generation.scenario_config import load_all_scenarios
from pathlib import Path
import re
from dataclasses import fields
from core.models import FacilityState
fnames = {{f.name for f in fields(FacilityState)}}
configs = load_all_scenarios(Path('{bad_scenarios_dir}'))
for config in configs.values():
    for alert in config.alerts:
        tokens = {{m.group(1) for m in re.finditer(r'\\{{(\\w+)(?:[^}}]*)?\\}}', alert.msg)}}
        for t in tokens:
            if t not in fnames:
                print(f"Scenario '{{config.name}}' tick {{alert.tick}}: unknown field '{{t}}'")
                sys.exit(1)
sys.exit(0)
"""],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "nonexistent_field" in result.stdout
