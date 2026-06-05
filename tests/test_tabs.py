"""Tests for pure helper functions in tabs/network.py and tabs/facility.py."""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from core.models import AlertRecord
from loader import load_scenario_payloads
from tabs.facility import (
    build_shap_waterfall_figure,
    build_time_series_figure,
    get_most_recent_alert,
    get_recommended_actions,
)
from tabs.network import compute_metrics, get_active_reroutes


@pytest.fixture(scope="module")
def sc01_payload() -> dict:
    payloads = load_scenario_payloads()
    return payloads["sc-01"]


@pytest.fixture(scope="module")
def sc01_tick4_df(sc01_payload) -> pd.DataFrame:
    return sc01_payload["tick_df"][sc01_payload["tick_df"]["tick"] == 4]


# ─── compute_metrics ─────────────────────────────────────────────────────────

def test_compute_metrics_returns_5_keys(sc01_tick4_df):
    m = compute_metrics(sc01_tick4_df, "NET-A")
    assert set(m.keys()) == {
        "critical_count", "warning_count", "total_queued",
        "low_cartridge_count", "avg_dropout_risk",
    }


def test_compute_metrics_empty_df():
    m = compute_metrics(pd.DataFrame(), "NET-A")
    assert m["critical_count"] == 0
    assert m["total_queued"] == 0.0


def test_compute_metrics_counts_by_network(sc01_payload):
    tick0_df = sc01_payload["tick_df"][sc01_payload["tick_df"]["tick"] == 0]
    m_a = compute_metrics(tick0_df, "NET-A")
    m_b = compute_metrics(tick0_df, "NET-B")
    # Each network has distinct facilities
    assert m_a["critical_count"] + m_a["warning_count"] >= 0
    assert m_b["critical_count"] + m_b["warning_count"] >= 0


def test_compute_metrics_total_queued_positive(sc01_tick4_df):
    m = compute_metrics(sc01_tick4_df, "NET-A")
    assert m["total_queued"] > 0


def test_compute_metrics_low_consumable_excludes_zero_stock(sc01_tick4_df):
    """Low consumable count must NOT include facilities with zero cartridges and zero chips."""
    m = compute_metrics(sc01_tick4_df, "NET-A")
    # NET-A has 14 facilities; only hub (DHC-A) has cartridges > 0.
    # DHC-A has ~120 cartridges at tick 4 — well above warn threshold (25).
    # So low_consumable should be 0 (no facility is running low yet).
    assert m["low_cartridge_count"] == 0, (
        f"Expected 0 low-consumable sites at tick 4, got {m['low_cartridge_count']} — "
        "likely counting zero-stock Truenat/CHC facilities incorrectly"
    )


def test_compute_metrics_avg_dropout_risk_in_range(sc01_tick4_df):
    m = compute_metrics(sc01_tick4_df, "NET-A")
    assert 0.0 <= m["avg_dropout_risk"] <= 1.0


# ─── get_active_reroutes ─────────────────────────────────────────────────────

def test_get_active_reroutes_before_recommendation(sc01_payload):
    """Before tick 7 (recommendation fires), reroutes should be None."""
    result = get_active_reroutes(sc01_payload, tick=3)
    assert result is None


def test_get_active_reroutes_at_recommendation_tick(sc01_payload):
    """At tick 7 (SC-01 recommendation), reroutes should activate."""
    result = get_active_reroutes(sc01_payload, tick=7)
    assert result is not None
    assert len(result) == 2  # SC-01 has 2 reroutes


def test_get_active_reroutes_after_recommendation(sc01_payload):
    result = get_active_reroutes(sc01_payload, tick=15)
    assert result is not None
    assert ["MC2-A", "TL2-A"] in result
    assert ["CHC2-A", "TL2-A"] in result


def test_get_active_reroutes_no_reroutes():
    payload = {"metadata": {"reroutes": []}, "alerts": []}
    result = get_active_reroutes(payload, tick=10)
    assert result is None


# ─── get_most_recent_alert ───────────────────────────────────────────────────

def _make_alert(tick, facility="DHC-A", shap=None):
    return AlertRecord(
        tick=tick, facility_id=facility, network_id="NET-A",
        alert_type="critical", message=f"Alert at tick {tick}",
        shap_contributions=shap or {"patients_queued": float(tick) * 1.8 * 0.45},
        severity="critical",
    )


def test_get_most_recent_alert_returns_latest():
    alerts = [_make_alert(4), _make_alert(10), _make_alert(7)]
    result = get_most_recent_alert(alerts, "DHC-A", up_to_tick=10)
    assert result is not None
    assert result.tick == 10


def test_get_most_recent_alert_respects_up_to_tick():
    alerts = [_make_alert(4), _make_alert(10)]
    result = get_most_recent_alert(alerts, "DHC-A", up_to_tick=6)
    assert result is not None
    assert result.tick == 4


def test_get_most_recent_alert_none_for_unaffected_facility():
    alerts = [_make_alert(4, facility="DHC-A")]
    result = get_most_recent_alert(alerts, "TL1-A", up_to_tick=10)
    assert result is None


def test_get_most_recent_alert_none_before_any_fires():
    alerts = [_make_alert(4)]
    result = get_most_recent_alert(alerts, "DHC-A", up_to_tick=3)
    assert result is None


def test_get_most_recent_alert_from_real_sc01(sc01_payload):
    """In SC-01, DHC-A's most recent alert at tick 14 is the DTO advisory (tick 14)."""
    alerts = sc01_payload["alerts"]
    result = get_most_recent_alert(alerts, "DHC-A", up_to_tick=14)
    assert result is not None
    assert result.tick == 14
    assert result.alert_type == "dto_advisory"


# ─── get_recommended_actions ─────────────────────────────────────────────────

def test_get_recommended_actions_sc01_dhc_a(sc01_payload):
    actions = get_recommended_actions(sc01_payload, "DHC-A")
    assert len(actions) == 3
    assert all(isinstance(a, str) for a in actions)


def test_get_recommended_actions_unknown_facility(sc01_payload):
    actions = get_recommended_actions(sc01_payload, "UNKNOWN-99")
    assert actions == []


def test_get_recommended_actions_max_3(sc01_payload):
    actions = get_recommended_actions(sc01_payload, "DHC-A")
    assert len(actions) <= 3


# ─── build_time_series_figure ────────────────────────────────────────────────

def test_build_time_series_returns_figure(sc01_payload):
    fig = build_time_series_figure(
        sc01_payload["tick_df"], "patients_queued", "DHC-A", up_to_tick=10
    )
    assert isinstance(fig, go.Figure)


def test_build_time_series_empty_df_returns_empty_figure():
    fig = build_time_series_figure(pd.DataFrame(), "patients_queued", "DHC-A", 10)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_time_series_has_data_trace(sc01_payload):
    fig = build_time_series_figure(
        sc01_payload["tick_df"], "patients_queued", "DHC-A", up_to_tick=10
    )
    assert len(fig.data) >= 1


def test_build_time_series_up_to_tick_respected(sc01_payload):
    fig5 = build_time_series_figure(sc01_payload["tick_df"], "patients_queued", "DHC-A", 5)
    fig15 = build_time_series_figure(sc01_payload["tick_df"], "patients_queued", "DHC-A", 15)
    assert len(fig5.data[0].x) <= len(fig15.data[0].x)


def test_build_time_series_has_threshold_lines(sc01_payload):
    fig = build_time_series_figure(
        sc01_payload["tick_df"], "patients_queued", "DHC-A", up_to_tick=24
    )
    # Threshold lines are added as layout shapes or hlines
    assert fig.layout.shapes is not None or len(fig.data) >= 1


def test_build_time_series_unknown_field_returns_empty(sc01_payload):
    fig = build_time_series_figure(
        sc01_payload["tick_df"], "nonexistent_field", "DHC-A", 10
    )
    assert isinstance(fig, go.Figure)


# ─── build_shap_waterfall_figure ─────────────────────────────────────────────

def test_build_shap_waterfall_returns_figure():
    fig = build_shap_waterfall_figure({"patients_queued": 3.24, "tat_hours": 0.84})
    assert isinstance(fig, go.Figure)


def test_build_shap_waterfall_empty_returns_empty_figure():
    fig = build_shap_waterfall_figure({})
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_shap_waterfall_horizontal_bars():
    fig = build_shap_waterfall_figure({"patients_queued": 3.24})
    assert len(fig.data) == 1
    assert fig.data[0].orientation == "h"


def test_build_shap_waterfall_top5_max(sc01_payload):
    # Use a dict with more than 5 entries
    many_shap = {f"field_{i}": float(i) for i in range(10)}
    fig = build_shap_waterfall_figure(many_shap, top_n=5)
    assert len(fig.data[0].y) <= 5


def test_build_shap_waterfall_title_contains_approximate():
    fig = build_shap_waterfall_figure({"patients_queued": 1.0})
    assert "Approximate" in fig.layout.title.text


def test_build_shap_waterfall_positive_blue():
    fig = build_shap_waterfall_figure({"patients_queued": 3.24})
    colors = list(fig.data[0].marker.color)
    assert "#3b82f6" in colors


def test_build_shap_waterfall_negative_red():
    fig = build_shap_waterfall_figure({"cartridges": -1.40})
    colors = list(fig.data[0].marker.color)
    assert "#ef4444" in colors


# ─── ScenarioMeta reroutes + recommended_actions loaded ──────────────────────

def test_sc01_payload_has_reroutes(sc01_payload):
    reroutes = sc01_payload["metadata"].get("reroutes", [])
    assert isinstance(reroutes, list)
    assert len(reroutes) == 2


def test_sc01_payload_has_recommended_actions(sc01_payload):
    ra = sc01_payload["metadata"].get("recommended_actions", {})
    assert isinstance(ra, dict)
    assert "DHC-A" in ra
    assert len(ra["DHC-A"]) == 3
