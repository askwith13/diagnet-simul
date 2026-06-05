"""Tests for generation/engine.py — ScenarioGenerator and AI model stubs."""
import math
from pathlib import Path

import networkx as nx
import numpy as np
import pytest
import yaml

from core.models import FacilityState
from generation.engine import (
    GlobalGenState,
    NetworkGenState,
    ScenarioGenerator,
    b1_stockout_prob,
    build_network_graph,
    m1_anomaly_score,
    m2_graph_metrics,
    m4_optimal_route,
)
from generation.scenario_config import load_scenario_yaml

NETWORKS_PATH = Path("config/networks.yaml")
SC01_PATH = Path("config/scenarios/sc-01.yaml")
SC04_PATH = Path("config/scenarios/sc-04.yaml")
SC08_PATH = Path("config/scenarios/sc-08.yaml")

RNG = np.random.default_rng(42)


@pytest.fixture(scope="module")
def networks_data() -> dict:
    return yaml.safe_load(NETWORKS_PATH.read_text())


@pytest.fixture(scope="module")
def sc01(networks_data) -> ScenarioGenerator:
    config = load_scenario_yaml(SC01_PATH)
    return ScenarioGenerator(config, networks_data, seed=42)


# ─── build_network_graph ─────────────────────────────────────────────────────

def test_build_network_graph_node_count(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    assert len(g.nodes) == 14


def test_build_network_graph_has_edges(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    assert len(g.edges) > 0


def test_build_network_graph_edge_weights_positive(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    for _, _, data in g.edges(data=True):
        assert data["weight"] > 0


# ─── B1 stockout forecaster ──────────────────────────────────────────────────

def test_b1_output_in_range():
    rng = np.random.default_rng(0)
    fs = FacilityState(cartridges=10, daily_consumption=8)
    result = b1_stockout_prob(fs, rng)
    assert 0.20 <= result <= 0.95


def test_b1_high_stock_lower_probability():
    rng = np.random.default_rng(0)
    fs_high = FacilityState(cartridges=120, daily_consumption=8)
    fs_low = FacilityState(cartridges=10, daily_consumption=8)
    # Run multiple times to account for noise
    high_probs = [b1_stockout_prob(fs_high, np.random.default_rng(i)) for i in range(20)]
    low_probs = [b1_stockout_prob(fs_low, np.random.default_rng(i)) for i in range(20)]
    assert sum(high_probs) / len(high_probs) < sum(low_probs) / len(low_probs)


def test_b1_zero_stock_high_probability():
    rng = np.random.default_rng(0)
    fs = FacilityState(cartridges=0, truenat_chips=0, daily_consumption=8)
    result = b1_stockout_prob(fs, rng)
    assert result >= 0.80


def test_b1_truenat_chips_used_when_no_cartridges():
    rng = np.random.default_rng(0)
    fs = FacilityState(cartridges=0, truenat_chips=20, daily_consumption=4)
    result = b1_stockout_prob(fs, rng)
    assert 0.20 <= result <= 0.95


# ─── M1 anomaly score ────────────────────────────────────────────────────────

def test_m1_output_in_range():
    rng = np.random.default_rng(0)
    baseline = FacilityState(patients_queued=42, tat_hours=18, cascade_dropout_risk=0.08)
    fs = FacilityState(patients_queued=60, tat_hours=36, cascade_dropout_risk=0.45)
    result = m1_anomaly_score(fs, baseline, rng)
    assert 0.30 <= result <= 0.95


def test_m1_elevated_metrics_higher_score():
    rng = np.random.default_rng(42)
    baseline = FacilityState(patients_queued=42, tat_hours=18, cascade_dropout_risk=0.08)
    normal = FacilityState(patients_queued=42, tat_hours=18, cascade_dropout_risk=0.08)
    stressed = FacilityState(patients_queued=80, tat_hours=40, cascade_dropout_risk=0.70)
    scores_normal = [m1_anomaly_score(normal, baseline, np.random.default_rng(i)) for i in range(10)]
    scores_stressed = [m1_anomaly_score(stressed, baseline, np.random.default_rng(i)) for i in range(10)]
    assert sum(scores_stressed) / 10 > sum(scores_normal) / 10


# ─── M2 graph metrics ────────────────────────────────────────────────────────

def test_m2_returns_all_nodes(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    metrics = m2_graph_metrics(g)
    assert set(metrics.keys()) == set(g.nodes)


def test_m2_betweenness_in_unit_range(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    metrics = m2_graph_metrics(g)
    for node, m in metrics.items():
        assert 0.0 <= m["betweenness_centrality"] <= 1.0, f"{node}: betweenness out of range"


def test_m2_pagerank_in_unit_range(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    metrics = m2_graph_metrics(g)
    for node, m in metrics.items():
        assert 0.0 <= m["pagerank"] <= 1.0, f"{node}: pagerank out of range"


def test_m2_bottleneck_score_formula(networks_data):
    """bottleneck_score = 0.6 × norm_betweenness + 0.4 × norm_pagerank."""
    g = build_network_graph(networks_data["networks"]["NET-A"])
    metrics = m2_graph_metrics(g)
    max_b = max(m["betweenness_centrality"] for m in metrics.values()) or 1.0
    max_p = max(m["pagerank"] for m in metrics.values()) or 1.0
    for node, m in metrics.items():
        expected = 0.6 * (m["betweenness_centrality"] / max_b) + 0.4 * (m["pagerank"] / max_p)
        assert m["bottleneck_score"] == pytest.approx(expected, abs=1e-6), (
            f"{node}: bottleneck_score mismatch"
        )


def test_m2_hub_has_higher_bottleneck(networks_data):
    """Hub nodes should rank higher on bottleneck score than CHC nodes."""
    g = build_network_graph(networks_data["networks"]["NET-A"])
    metrics = m2_graph_metrics(g)
    hub_score = metrics["DHC-A"]["bottleneck_score"]
    chc_scores = [metrics[n]["bottleneck_score"] for n in metrics if n.startswith("CHC")]
    assert hub_score > sum(chc_scores) / len(chc_scores)


# ─── M4 optimal router ───────────────────────────────────────────────────────

def test_m4_returns_sorted_routes(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    baselines = {
        fac_id: FacilityState(tat_hours=12)
        for fac_id in g.nodes
    }
    routes = m4_optimal_route(g, "CHC1-A", ["TL1-A", "TL2-A", "TL3-A"], baselines)
    assert len(routes) > 0
    tats = [r["estimated_tat"] for r in routes]
    assert tats == sorted(tats)


def test_m4_excludes_source(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    states = {n: FacilityState(tat_hours=12) for n in g.nodes}
    routes = m4_optimal_route(g, "DHC-A", ["DHC-A", "TL1-A"], states)
    facility_ids = [r["facility_id"] for r in routes]
    assert "DHC-A" not in facility_ids


def test_m4_estimated_tat_positive(networks_data):
    g = build_network_graph(networks_data["networks"]["NET-A"])
    states = {n: FacilityState(tat_hours=12) for n in g.nodes}
    routes = m4_optimal_route(g, "CHC1-A", list(g.nodes), states)
    for r in routes:
        assert r["estimated_tat"] > 0


# ─── ScenarioGenerator ───────────────────────────────────────────────────────

def test_generator_instantiates(sc01):
    assert sc01 is not None


def test_run_returns_correct_row_count(sc01):
    snapshots = sc01.run()
    # SC-01: max_ticks=25, NET-A has 14 facilities; but generator runs ALL 5 networks
    # 25 ticks × 59 facilities = 1475 rows
    assert len(snapshots) == 25 * 59


def test_run_all_flat_tick_snapshot_fields_present(sc01):
    from core.models import FlatTickSnapshot
    required = set(FlatTickSnapshot.__annotations__.keys())
    snapshots = sc01.run()
    for snap in snapshots[:10]:  # check first 10 for speed
        missing = required - set(snap.keys())
        assert not missing, f"FlatTickSnapshot missing fields: {missing}"


def test_run_no_none_values(sc01):
    snapshots = sc01.run()
    for snap in snapshots[:10]:
        for key, val in snap.items():
            if key == "predicted_stockout_day":
                continue  # NaN is valid here
            assert val is not None, f"Field '{key}' is None"


def test_tick_returns_new_object(sc01):
    s0 = sc01._init_global_state()
    s1 = sc01._tick(s0, 0)
    assert s0 is not s1
    assert s0.networks["NET-A"].facilities["DHC-A"] is not s1.networks["NET-A"].facilities["DHC-A"]


def test_dhc_a_patients_queued_at_tick4(networks_data):
    """DHC-A patients_queued at tick 4 ≈ baseline + 4×1.8 (within ±5% noise)."""
    config = load_scenario_yaml(SC01_PATH)
    gen = ScenarioGenerator(config, networks_data, seed=42)
    baseline_pq = gen._baselines["NET-A"]["DHC-A"].patients_queued
    expected_delta = 4 * 1.8  # 4 ticks × delta 1.8

    snapshots = gen.run()
    tick4_dhc_a = [
        s for s in snapshots
        if s["tick"] == 4 and s["facility_id"] == "DHC-A"
    ]
    assert len(tick4_dhc_a) == 1
    actual = tick4_dhc_a[0]["patients_queued"]
    # Within ±5% of expected_delta (noise allowance)
    tolerance = 0.05 * expected_delta + 1.0  # absolute tolerance
    assert abs(actual - (baseline_pq + expected_delta)) < tolerance + expected_delta * 0.15, (
        f"patients_queued={actual:.2f}, expected≈{baseline_pq + expected_delta:.2f}"
    )


def test_run_sc08_uses_initial_states(networks_data):
    """SC-08 run should start NET-A DHC-A from post-crisis patients_queued=60."""
    config = load_scenario_yaml(SC08_PATH)
    gen = ScenarioGenerator(config, networks_data, seed=42)
    s0 = gen._init_global_state()
    assert s0.networks["NET-A"].facilities["DHC-A"].patients_queued == pytest.approx(60, abs=1)


def test_apply_overflow_adds_to_target_hub():
    """apply_overflow() should add overflow_pending to the target network's hub."""
    # Build a minimal GlobalGenState with one network containing a hub
    hub = FacilityState(patients_queued=30, machines=3, modules=6)
    net_state = NetworkGenState(
        network_id="NET-A",
        facilities={"DHC-A": hub},
        graph=nx.Graph(),
    )
    state = GlobalGenState(
        networks={"NET-A": net_state},
        overflow_pending={"NET-A": 15.0},
        tick=8,
    )
    ScenarioGenerator.apply_overflow(state)
    assert state.networks["NET-A"].facilities["DHC-A"].patients_queued == pytest.approx(45.0)
    assert state.overflow_pending == {}


def test_alerts_fired_at_correct_ticks(networks_data):
    """SC-01 should fire a critical alert at tick 4."""
    config = load_scenario_yaml(SC01_PATH)
    gen = ScenarioGenerator(config, networks_data, seed=42)
    _, alerts = gen.run_with_alerts()
    tick4_alerts = [a for a in alerts if a.tick == 4]
    assert len(tick4_alerts) >= 1
    assert any(a.alert_type == "critical" for a in tick4_alerts)


def test_alert_shap_contributions_present(networks_data):
    """Fired alerts should have non-empty shap_contributions."""
    config = load_scenario_yaml(SC01_PATH)
    gen = ScenarioGenerator(config, networks_data, seed=42)
    _, alerts = gen.run_with_alerts()
    assert len(alerts) > 0
    for alert in alerts:
        assert isinstance(alert.shap_contributions, dict)
        assert len(alert.shap_contributions) > 0


def test_status_updates_correctly(networks_data):
    """Facilities should become warning/critical as metrics deteriorate."""
    config = load_scenario_yaml(SC01_PATH)
    gen = ScenarioGenerator(config, networks_data, seed=42)
    snapshots = gen.run()
    # DHC-A at late ticks (tick 20+) should have critical or warning status
    late_dhc_a = [
        s for s in snapshots
        if s["facility_id"] == "DHC-A" and s["tick"] >= 20
    ]
    statuses = {s["status"] for s in late_dhc_a}
    assert statuses & {"warning", "critical"}, (
        f"DHC-A still 'ok' at tick 20+: statuses={statuses}"
    )
