"""Tests for loader.py — data loading and validation helpers."""
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from core.models import FlatTickSnapshot, ScenarioPayload
from loader import (
    load_metadata,
    load_scenario_payloads,
    validate_data_exists,
)

DATA_DIR = Path("data/scenarios")
METADATA_PATH = DATA_DIR / "metadata.json"


# ─── load_metadata ────────────────────────────────────────────────────────────

def test_load_metadata_returns_dict():
    meta = load_metadata()
    assert isinstance(meta, dict)


def test_load_metadata_has_schema_version():
    meta = load_metadata()
    assert meta["schema_version"] == "1.0.0"


def test_load_metadata_has_8_scenarios():
    meta = load_metadata()
    assert len(meta["scenarios"]) == 8


def test_load_metadata_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_metadata(tmp_path / "nonexistent.json")


# ─── validate_data_exists ─────────────────────────────────────────────────────

def test_validate_data_exists_returns_empty_when_all_present():
    meta = load_metadata()
    missing = validate_data_exists(meta)
    assert missing == [], f"Unexpected missing files: {missing}"


def test_validate_data_exists_detects_missing_parquet(tmp_path):
    """If a parquet file is absent, its path appears in the missing list."""
    meta = load_metadata()
    # Take the first scenario's parquet and check with a fake data_dir
    first_sc = meta["scenarios"][0]
    parquet_name = Path(first_sc["parquet_path"]).name

    # Copy real data to tmp_path but omit one parquet
    (tmp_path / "scenarios").mkdir()
    for entry in meta["scenarios"]:
        parquet = DATA_DIR / Path(entry["parquet_path"]).name
        alerts = DATA_DIR / Path(entry["alerts_path"]).name
        if Path(entry["parquet_path"]).name != parquet_name:
            shutil.copy(parquet, tmp_path / entry["parquet_path"])
        shutil.copy(alerts, tmp_path / entry["alerts_path"])

    missing = validate_data_exists(meta, tmp_path / "scenarios")
    assert any(parquet_name in m for m in missing)


def test_validate_data_exists_returns_list():
    meta = load_metadata()
    result = validate_data_exists(meta)
    assert isinstance(result, list)


# ─── load_scenario_payloads ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def payloads() -> dict:
    return load_scenario_payloads()


def test_load_scenario_payloads_returns_8_entries(payloads):
    assert len(payloads) == 8


def test_load_scenario_payloads_keys(payloads):
    expected = {f"sc-0{i}" for i in range(1, 9)}
    assert set(payloads.keys()) == expected


def test_scenario_payload_has_tick_df(payloads):
    for sc_id, payload in payloads.items():
        assert "tick_df" in payload
        assert isinstance(payload["tick_df"], pd.DataFrame), f"{sc_id}: tick_df not DataFrame"


def test_scenario_payload_has_alerts(payloads):
    for sc_id, payload in payloads.items():
        assert "alerts" in payload
        assert isinstance(payload["alerts"], list), f"{sc_id}: alerts not list"


def test_scenario_payload_has_metadata(payloads):
    for sc_id, payload in payloads.items():
        assert "metadata" in payload
        meta = payload["metadata"]
        assert "id" in meta
        assert "display_name" in meta
        assert "tick_count" in meta


def test_tick_df_column_count(payloads):
    from core.models import FlatTickSnapshot
    expected = len(FlatTickSnapshot.__annotations__)  # 25
    for sc_id, payload in payloads.items():
        actual = payload["tick_df"].shape[1]
        assert actual == expected, f"{sc_id}: expected {expected} cols, got {actual}"


def test_tick_df_row_count(payloads):
    for sc_id, payload in payloads.items():
        tick_count = payload["metadata"]["tick_count"]
        expected_rows = tick_count * 59
        actual_rows = payload["tick_df"].shape[0]
        assert actual_rows == expected_rows, (
            f"{sc_id}: expected {expected_rows} rows, got {actual_rows}"
        )


def test_sc01_alerts_non_empty(payloads):
    """SC-01 should have 4 scripted alerts."""
    assert len(payloads["sc-01"]["alerts"]) == 4


def test_alert_shap_contributions_loaded(payloads):
    for sc_id, payload in payloads.items():
        for alert in payload["alerts"]:
            assert isinstance(alert.shap_contributions, dict)
            assert len(alert.shap_contributions) > 0, (
                f"{sc_id}: alert at tick {alert.tick} has empty shap_contributions"
            )


def test_metadata_display_name_sc01(payloads):
    assert payloads["sc-01"]["metadata"]["display_name"] == "Network bottleneck"


def test_load_scenario_payloads_missing_metadata_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_scenario_payloads(tmp_path / "metadata.json", tmp_path)


# ─── app.py structure (import safety check) ──────────────────────────────────

def test_loader_has_no_streamlit_import():
    """loader.py must not import streamlit."""
    loader_source = Path("loader.py").read_text()
    assert "import streamlit" not in loader_source
    assert "from streamlit" not in loader_source


def test_session_has_no_streamlit_import():
    session_source = Path("session.py").read_text()
    assert "import streamlit" not in session_source


def test_playback_has_no_streamlit_import():
    playback_source = Path("playback.py").read_text()
    assert "import streamlit" not in playback_source
