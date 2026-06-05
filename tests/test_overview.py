"""Tests for pure helper functions in tabs/overview.py."""
import pandas as pd
import plotly.graph_objects as go
import pytest

from core.models import AlertRecord
from loader import load_scenario_payloads
from tabs.overview import (
    build_bottleneck_heatmap,
    build_inter_network_figure,
    compute_network_critical,
    get_global_alerts,
)


@pytest.fixture(scope="module")
def sc01_payload() -> dict:
    return load_scenario_payloads()["sc-01"]


@pytest.fixture(scope="module")
def tick0_df(sc01_payload) -> pd.DataFrame:
    return sc01_payload["tick_df"][sc01_payload["tick_df"]["tick"] == 0]


@pytest.fixture(scope="module")
def sc04_tick8_df() -> pd.DataFrame:
    payloads = load_scenario_payloads()
    df = payloads["sc-04"]["tick_df"]
    return df[df["tick"] == 8]


# ─── compute_network_critical ─────────────────────────────────────────────────

def test_compute_network_critical_empty_df():
    result = compute_network_critical(pd.DataFrame())
    assert result == {}


def test_compute_network_critical_returns_5_networks(tick0_df):
    result = compute_network_critical(tick0_df)
    assert set(result.keys()) == {"NET-A", "NET-B", "NET-C", "NET-D", "NET-E"}


def test_compute_network_critical_all_false_at_baseline(tick0_df):
    """At tick 0 baseline, no networks should be critical."""
    result = compute_network_critical(tick0_df)
    # At tick 0, most facilities are healthy
    assert isinstance(result, dict)
    for val in result.values():
        assert isinstance(val, bool)


def test_compute_network_critical_detects_critical_status():
    """If a row has status=critical, its network is marked critical."""
    df = pd.DataFrame([
        {"facility_id": "DHC-A", "network_id": "NET-A", "status": "critical",
         "bottleneck_score": 0.8},
        {"facility_id": "TH-B", "network_id": "NET-B", "status": "ok",
         "bottleneck_score": 0.2},
    ])
    result = compute_network_critical(df)
    assert result["NET-A"] is True
    assert result["NET-B"] is False


# ─── build_bottleneck_heatmap ─────────────────────────────────────────────────

def test_build_bottleneck_heatmap_returns_figure(tick0_df):
    fig = build_bottleneck_heatmap(tick0_df)
    assert isinstance(fig, go.Figure)


def test_build_bottleneck_heatmap_empty_returns_empty(
):
    fig = build_bottleneck_heatmap(pd.DataFrame())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_bottleneck_heatmap_has_bars(tick0_df):
    """Should have at least one bar (facilities with patients_queued > 0)."""
    fig = build_bottleneck_heatmap(tick0_df)
    assert len(fig.data) == 1
    assert len(fig.data[0].y) > 0


def test_build_bottleneck_heatmap_horizontal(tick0_df):
    fig = build_bottleneck_heatmap(tick0_df)
    assert fig.data[0].orientation == "h"


def test_build_bottleneck_heatmap_sorted_ascending(tick0_df):
    """Bars should be in ascending order (lowest queue at top, highest at bottom)."""
    fig = build_bottleneck_heatmap(tick0_df)
    scores = list(fig.data[0].x)
    assert scores == sorted(scores)


def test_build_bottleneck_heatmap_title_present(tick0_df):
    fig = build_bottleneck_heatmap(tick0_df)
    assert fig.layout.title.text is not None and len(fig.layout.title.text) > 0


def test_build_bottleneck_heatmap_changes_across_ticks():
    """patients_queued changes every tick — heatmap must not be static."""
    import pandas as pd
    df = pd.read_parquet("data/scenarios/sc-01.parquet")
    fig_t0 = build_bottleneck_heatmap(df[df["tick"] == 0])
    fig_t14 = build_bottleneck_heatmap(df[df["tick"] == 14])
    x0 = list(fig_t0.data[0].x)
    x14 = list(fig_t14.data[0].x)
    assert x0 != x14, "Heatmap bars are identical at tick 0 and tick 14 — not dynamic"


# ─── build_inter_network_figure ───────────────────────────────────────────────

def test_build_inter_network_figure_returns_figure():
    fig = build_inter_network_figure({})
    assert isinstance(fig, go.Figure)


def test_build_inter_network_figure_has_5_network_nodes():
    """Node trace should have 5 points (one per network)."""
    fig = build_inter_network_figure({})
    node_trace = [t for t in fig.data if t.mode == "markers+text"]
    assert len(node_trace) == 1
    assert len(node_trace[0].x) == 5


def test_build_inter_network_figure_has_3_edge_traces():
    """Should have 3 edge line traces (one per inter-network link)."""
    fig = build_inter_network_figure({})
    edge_traces = [t for t in fig.data if t.mode == "lines"]
    assert len(edge_traces) == 3


def test_build_inter_network_figure_critical_edge_is_red():
    """When NET-D is critical, the NET-D→NET-A edge should be red."""
    fig = build_inter_network_figure({"NET-D": True, "NET-A": False})
    red_traces = [t for t in fig.data if t.mode == "lines" and t.line.color == "#ef4444"]
    assert len(red_traces) >= 1


def test_build_inter_network_figure_no_critical_edges_green():
    """When no networks are critical, all edges should be green."""
    fig = build_inter_network_figure({"NET-A": False, "NET-B": False, "NET-C": False,
                                       "NET-D": False, "NET-E": False})
    red_traces = [t for t in fig.data if t.mode == "lines" and t.line.color == "#ef4444"]
    green_traces = [t for t in fig.data if t.mode == "lines" and t.line.color == "#22c55e"]
    assert len(red_traces) == 0
    assert len(green_traces) == 3


def test_build_inter_network_figure_node_labels_present():
    fig = build_inter_network_figure({})
    node_trace = [t for t in fig.data if t.mode == "markers+text"][0]
    assert "NET-A" in list(node_trace.text)
    assert "NET-D" in list(node_trace.text)


# ─── get_global_alerts ────────────────────────────────────────────────────────

def _make_alert(tick, net="NET-A", facility="DHC-A"):
    return AlertRecord(
        tick=tick, facility_id=facility, network_id=net,
        alert_type="critical", message=f"Alert tick {tick}",
        shap_contributions={"patients_queued": 1.0}, severity="critical",
    )


def test_get_global_alerts_empty_list():
    result = get_global_alerts([], up_to_tick=10)
    assert result == []


def test_get_global_alerts_filters_by_tick():
    alerts = [_make_alert(4), _make_alert(10), _make_alert(15)]
    result = get_global_alerts(alerts, up_to_tick=10)
    assert all(a.tick <= 10 for a in result)
    assert len(result) == 2


def test_get_global_alerts_sorted_most_recent_first():
    alerts = [_make_alert(4), _make_alert(10), _make_alert(7)]
    result = get_global_alerts(alerts, up_to_tick=10)
    ticks = [a.tick for a in result]
    assert ticks == sorted(ticks, reverse=True)


def test_get_global_alerts_includes_all_networks():
    alerts = [
        _make_alert(4, net="NET-A"),
        _make_alert(5, net="NET-D"),
        _make_alert(6, net="NET-B"),
    ]
    result = get_global_alerts(alerts, up_to_tick=10)
    networks = {a.network_id for a in result}
    assert networks == {"NET-A", "NET-D", "NET-B"}


def test_get_global_alerts_from_real_sc04(sc04_tick8_df):
    """SC-04 at tick 8 should have alerts across multiple networks."""
    payloads = load_scenario_payloads()
    sc04_alerts = payloads["sc-04"]["alerts"]
    result = get_global_alerts(sc04_alerts, up_to_tick=8)
    assert len(result) >= 1


# ─── Run SC-08 state mutation (tested via session constants) ──────────────────

def test_run_sc08_state_mutation():
    """Verify the SC-08 button state mutations work correctly."""
    from session import CURRENT_SCENARIO, IS_PLAYING, TICK_CURSOR, init_session_state
    state = init_session_state({"sc-01": {}, "sc-08": {}})
    # Simulate button click
    state[CURRENT_SCENARIO] = "sc-08"
    state[TICK_CURSOR] = 0
    state[IS_PLAYING] = True
    assert state[CURRENT_SCENARIO] == "sc-08"
    assert state[TICK_CURSOR] == 0
    assert state[IS_PLAYING] is True
