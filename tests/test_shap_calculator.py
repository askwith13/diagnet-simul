"""Tests for generation/shap_calculator.py."""
import pytest

from core.models import FacilityState
from generation.scenario_config import load_scenario_yaml
from generation.shap_calculator import compute_shap, generate_alert_shap

SC01_PATH = "config/scenarios/sc-01.yaml"


# ─── compute_shap ────────────────────────────────────────────────────────────

def test_compute_shap_exact_value():
    assert compute_shap(1.8, 0.45) == pytest.approx(0.81)


def test_compute_shap_zero_delta():
    assert compute_shap(0.0, 0.45) == 0.0


def test_compute_shap_zero_weight():
    assert compute_shap(1.8, 0.0) == 0.0


def test_compute_shap_negative_delta():
    assert compute_shap(-1.4, 0.55) == pytest.approx(-0.77)


def test_compute_shap_is_delta_times_weight():
    for delta, weight in [(2.5, 0.3), (0.04, 0.2), (1.2, 0.4)]:
        assert compute_shap(delta, weight) == pytest.approx(delta * weight)


# ─── generate_alert_shap ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sc01():
    return load_scenario_yaml(SC01_PATH)


def test_generate_alert_shap_sc01_tick4_worked_example(sc01):
    """PRD §7 worked example: patients_queued=3.24, tat_hours=0.84, dropout=0.032."""
    alert = sc01.alerts[0]   # tick=4, facility=DHC-A
    assert alert.tick == 4
    fs = FacilityState()

    shap = generate_alert_shap(alert, fs, sc01)

    assert shap["patients_queued"] == pytest.approx(3.24, abs=0.01)
    assert shap["tat_hours"] == pytest.approx(0.84, abs=0.01)
    assert shap["cascade_dropout_risk"] == pytest.approx(0.032, abs=0.01)


def test_generate_alert_shap_sorted_by_abs_descending(sc01):
    alert = sc01.alerts[0]
    fs = FacilityState()
    shap = generate_alert_shap(alert, fs, sc01)

    values = list(shap.values())
    assert values == sorted(values, key=abs, reverse=True)


def test_generate_alert_shap_at_most_5_entries(sc01):
    alert = sc01.alerts[0]
    fs = FacilityState()
    shap = generate_alert_shap(alert, fs, sc01)
    assert len(shap) <= 5


def test_generate_alert_shap_empty_for_unaffected_facility(sc01):
    """Facility not in per_tick_deltas → empty dict."""
    from generation.scenario_config import AlertConfig
    alien_alert = AlertConfig(
        tick=4,
        type="critical",
        severity="critical",
        recipient="lab_supervisor",
        facility="CHC99-Z",   # not in sc01 per_tick_deltas
        msg="test",
    )
    fs = FacilityState()
    shap = generate_alert_shap(alien_alert, fs, sc01)
    assert shap == {}


def test_generate_alert_shap_formula_at_tick8(sc01):
    """At tick 8: shap = delta × weight × 8."""
    from generation.scenario_config import AlertConfig
    alert8 = AlertConfig(
        tick=8,
        type="critical",
        severity="critical",
        recipient="dto",
        facility="DHC-A",
        msg="test",
    )
    fs = FacilityState()
    shap = generate_alert_shap(alert8, fs, sc01)

    # patients_queued: 1.8 × 0.45 × 8 = 6.48
    assert shap["patients_queued"] == pytest.approx(1.8 * 0.45 * 8, rel=1e-6)
    # tat_hours: 0.6 × 0.35 × 8 = 1.68
    assert shap["tat_hours"] == pytest.approx(0.6 * 0.35 * 8, rel=1e-6)


def test_generate_alert_shap_zero_at_tick0(sc01):
    """At tick 0: shap_f = delta × weight × 0 = 0 for all fields."""
    from generation.scenario_config import AlertConfig
    alert0 = AlertConfig(
        tick=0,
        type="info",
        severity="info",
        recipient="dto",
        facility="DHC-A",
        msg="test",
    )
    fs = FacilityState()
    shap = generate_alert_shap(alert0, fs, sc01)
    for val in shap.values():
        assert val == pytest.approx(0.0)


def test_generate_alert_shap_facility_state_not_required(sc01):
    """facility_state is accepted but not used — any FacilityState gives same result."""
    alert = sc01.alerts[0]
    shap_default = generate_alert_shap(alert, FacilityState(), sc01)
    shap_stressed = generate_alert_shap(
        alert,
        FacilityState(patients_queued=99, tat_hours=50),
        sc01,
    )
    assert shap_default == shap_stressed


# ─── Integration: engine uses shap_calculator ─────────────────────────────────

def test_engine_alerts_use_shap_calculator():
    """Alerts fired by the engine should match shap_calculator output."""
    import yaml
    from pathlib import Path
    from generation.engine import ScenarioGenerator

    networks_data = yaml.safe_load(Path("config/networks.yaml").read_text())
    sc01_config = load_scenario_yaml(SC01_PATH)
    gen = ScenarioGenerator(sc01_config, networks_data, seed=42)
    _, alerts = gen.run_with_alerts()

    tick4_alert = next((a for a in alerts if a.tick == 4), None)
    assert tick4_alert is not None

    # Re-compute expected SHAP via shap_calculator directly
    alert_cfg = sc01_config.alerts[0]
    expected_shap = generate_alert_shap(alert_cfg, FacilityState(), sc01_config)

    assert tick4_alert.shap_contributions == pytest.approx(expected_shap, abs=1e-6)
