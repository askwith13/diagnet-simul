"""Tests for generation/scenario_config.py — config loader and validator."""
from pathlib import Path

import pytest

from generation.scenario_config import (
    AlertConfig,
    ScenarioConfig,
    all_facility_ids,
    load_all_scenarios,
    load_networks_yaml,
    load_scenario_yaml,
    validate_config,
)

SC01_PATH = Path("config/scenarios/sc-01.yaml")
SC08_PATH = Path("config/scenarios/sc-08.yaml")


# ---------------------------------------------------------------------------
# load_networks_yaml
# ---------------------------------------------------------------------------

def test_load_networks_yaml_returns_5_networks():
    networks = load_networks_yaml()
    assert set(networks.keys()) == {"NET-A", "NET-B", "NET-C", "NET-D", "NET-E"}


def test_load_networks_yaml_net_a_has_14_facilities():
    networks = load_networks_yaml()
    assert len(networks["NET-A"]) == 14


def test_all_facility_ids_returns_59():
    networks = load_networks_yaml()
    assert len(all_facility_ids(networks)) == 59


def test_dhc_a_in_net_a():
    networks = load_networks_yaml()
    assert "DHC-A" in networks["NET-A"]


# ---------------------------------------------------------------------------
# load_scenario_yaml
# ---------------------------------------------------------------------------

def test_load_scenario_yaml_returns_scenario_config():
    config = load_scenario_yaml(SC01_PATH)
    assert isinstance(config, ScenarioConfig)


def test_load_scenario_yaml_sc01_fields():
    config = load_scenario_yaml(SC01_PATH)
    assert config.scenario_id == "sc-01"
    assert config.name == "Network bottleneck"
    assert config.primary_network == "NET-A"
    assert config.max_ticks == 25
    assert "DHC-A" in config.affected_facilities


def test_load_scenario_yaml_sc01_per_tick_deltas():
    config = load_scenario_yaml(SC01_PATH)
    assert "DHC-A" in config.per_tick_deltas
    deltas = config.per_tick_deltas["DHC-A"]
    assert "patients_queued" in deltas
    assert deltas["patients_queued"] == pytest.approx(1.8)


def test_load_scenario_yaml_sc01_shap_weights():
    config = load_scenario_yaml(SC01_PATH)
    assert "patients_queued" in config.shap_weights
    assert "tat_hours" in config.shap_weights
    assert config.shap_weights["patients_queued"] == pytest.approx(0.45)


def test_load_scenario_yaml_sc01_alerts():
    config = load_scenario_yaml(SC01_PATH)
    assert len(config.alerts) == 4
    first = config.alerts[0]
    assert isinstance(first, AlertConfig)
    assert first.tick == 4
    assert first.type == "critical"
    assert first.facility == "DHC-A"


def test_load_scenario_yaml_sc01_reroutes():
    config = load_scenario_yaml(SC01_PATH)
    assert len(config.reroutes) == 2
    assert ["MC2-A", "TL2-A"] in config.reroutes


def test_load_scenario_yaml_sc01_recommended_actions():
    config = load_scenario_yaml(SC01_PATH)
    assert "DHC-A" in config.recommended_actions
    actions = config.recommended_actions["DHC-A"]
    assert len(actions) == 3
    assert all(isinstance(a, str) for a in actions)


def test_load_scenario_yaml_sc08_has_initial_states():
    config = load_scenario_yaml(SC08_PATH)
    assert config.initial_states is not None
    assert "NET-A" in config.initial_states
    assert "NET-D" in config.initial_states


def test_load_scenario_yaml_sc08_has_impact_metrics():
    config = load_scenario_yaml(SC08_PATH)
    assert config.impact_metrics is not None
    assert "total_patients_queued_reduction" in config.impact_metrics


def test_load_scenario_yaml_sc01_initial_states_none():
    config = load_scenario_yaml(SC01_PATH)
    assert config.initial_states is None


# ---------------------------------------------------------------------------
# load_all_scenarios
# ---------------------------------------------------------------------------

def test_load_all_scenarios_returns_8():
    configs = load_all_scenarios()
    assert len(configs) == 8


def test_load_all_scenarios_keys():
    configs = load_all_scenarios()
    expected = {f"sc-0{i}" for i in range(1, 9)}
    assert set(configs.keys()) == expected


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------

@pytest.fixture
def known_ids() -> set[str]:
    networks = load_networks_yaml()
    return all_facility_ids(networks)


def test_validate_config_passes_for_sc01(known_ids):
    config = load_scenario_yaml(SC01_PATH)
    validate_config(config, known_ids)  # must not raise


def test_validate_config_passes_for_all_8_scenarios(known_ids):
    for config in load_all_scenarios().values():
        validate_config(config, known_ids)  # must not raise for any scenario


def test_validate_config_raises_for_unknown_facility_in_affected(known_ids):
    config = load_scenario_yaml(SC01_PATH)
    config.affected_facilities.append("DHC-X")
    with pytest.raises(ValueError, match="Unknown facility 'DHC-X'"):
        validate_config(config, known_ids)


def test_validate_config_raises_for_unknown_facility_in_deltas(known_ids):
    config = load_scenario_yaml(SC01_PATH)
    config.per_tick_deltas["DHC-FAKE"] = {"patients_queued": 1.0}
    config.shap_weights["patients_queued"] = 1.0
    with pytest.raises(ValueError, match="Unknown facility 'DHC-FAKE'"):
        validate_config(config, known_ids)


def test_validate_config_raises_for_missing_shap_weight(known_ids):
    config = load_scenario_yaml(SC01_PATH)
    # Remove a shap_weight that has a matching delta field
    del config.shap_weights["patients_queued"]
    with pytest.raises(ValueError, match="shap_weights missing entries"):
        validate_config(config, known_ids)


def test_validate_config_error_message_names_scenario(known_ids):
    config = load_scenario_yaml(SC01_PATH)
    config.affected_facilities.append("UNKNOWN-99")
    with pytest.raises(ValueError, match="Network bottleneck"):
        validate_config(config, known_ids)
