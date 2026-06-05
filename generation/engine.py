"""Scenario generation engine — build-time only.

MUST NOT be imported by app.py, viz/, or tabs/.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
from scipy import stats

from core.models import AlertRecord, FacilityState, FlatTickSnapshot, safe_format
from generation.scenario_config import ScenarioConfig, load_networks_yaml
from generation.shap_calculator import generate_alert_shap

# ─── Global thresholds (PRD §5.1) used for status computation ────────────────

_CRITICAL: dict[str, tuple[str, float]] = {
    # (direction, value): "above" means critical if field > value; "below" if field < value
    "patients_queued":      ("above", 55),
    "cartridges":           ("below", 10),
    "truenat_chips":        ("below", 5),
    "tat_hours":            ("above", 36),
    "hr_on_shift":          ("below", 1),
    "bayesian_stockout_prob": ("above", 0.70),
    "cascade_dropout_risk": ("above", 0.60),
    "machines":             ("below", 1),
}
_WARN: dict[str, tuple[str, float]] = {
    "patients_queued":      ("above", 35),
    "cartridges":           ("below", 25),
    "truenat_chips":        ("below", 15),
    "tat_hours":            ("above", 24),
    "hr_on_shift":          ("below", 2),
    "bayesian_stockout_prob": ("above", 0.40),
    "cascade_dropout_risk": ("above", 0.35),
}

# Fields that must be clamped to [0, 1]
_RATE_FIELDS = frozenset({
    "smear_positivity_rate", "specimen_rejection_rate",
    "referral_completion_rate", "bayesian_stockout_prob", "cascade_dropout_risk",
})
# Fields that are non-negative counts/floats
_COUNT_FIELDS = frozenset({
    "patients_queued", "cartridges", "truenat_chips", "travel_time_min",
    "tat_hours", "hr_on_shift", "samples_per_module_per_day", "daily_consumption",
})
# Fields stored as integers
_INT_FIELDS = frozenset({"machines", "modules", "chw_available"})


# ─── Internal mutable state (generation-only) ────────────────────────────────

@dataclass
class NetworkGenState:
    """Mutable per-network state during generation."""
    network_id: str
    facilities: dict[str, FacilityState]
    graph: nx.Graph


@dataclass
class GlobalGenState:
    """Mutable global state across all 5 networks during generation."""
    networks: dict[str, NetworkGenState]
    overflow_pending: dict[str, float]   # target_network_id -> patient count
    tick: int = 0
    fired_alerts: list[AlertRecord] = field(default_factory=list)


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_network_graph(net_data: dict) -> nx.Graph:
    """Build an undirected NetworkX graph from a single network's YAML data."""
    g = nx.Graph()
    g.add_nodes_from(net_data["facilities"].keys())
    for link in net_data.get("links", []):
        src, dst, travel_time = link
        g.add_edge(src, dst, weight=float(travel_time))
    return g


# ─── AI model stubs ──────────────────────────────────────────────────────────

def b1_stockout_prob(fs: FacilityState, rng: np.random.Generator) -> float:
    """B1: Bayesian stockout forecaster stub.
    Returns P(stock ≤ 0 in 14 days) ∈ [0.20, 0.95].
    Uses logistic curve on days-of-stock vs 7-day half-life.
    """
    stock = fs.cartridges if fs.cartridges > 0 else fs.truenat_chips
    if fs.daily_consumption <= 0 or stock <= 0:
        # No consumption or no stock — either no concern or already depleted
        base = 0.90 if stock <= 0 and fs.daily_consumption > 0 else 0.20
        return float(np.clip(base + rng.normal(0, 0.02), 0.20, 0.95))

    days_remaining = stock / fs.daily_consumption
    # Logistic: P ≈ 0.5 at 7 days remaining, →0.95 at 0 days, →0.20 at 14+ days
    raw = 1.0 / (1.0 + math.exp(0.35 * (days_remaining - 7.0)))
    return float(np.clip(raw + rng.normal(0, 0.02), 0.20, 0.95))


def m1_anomaly_score(
    fs: FacilityState,
    baseline: FacilityState,
    rng: np.random.Generator,
) -> float:
    """M1: Isolation Forest stub via Z-score on composite anomaly index.
    Returns anomaly score ∈ [0.30, 0.95]; threshold 0.75.
    """
    ratios = []
    if baseline.patients_queued > 0:
        ratios.append(fs.patients_queued / baseline.patients_queued)
    if baseline.tat_hours > 0:
        ratios.append(fs.tat_hours / baseline.tat_hours)
    if baseline.cascade_dropout_risk > 0:
        ratios.append(fs.cascade_dropout_risk / baseline.cascade_dropout_risk)

    if not ratios:
        return 0.30

    composite = sum(ratios) / len(ratios)
    # CDF of composite ratio: mean=1.0 (baseline), scale=0.4
    # Shift result to [0.30, 0.95] range
    raw = float(stats.norm.cdf(composite, loc=1.0, scale=0.4)) * 0.65 + 0.30
    return float(np.clip(raw + rng.normal(0, 0.015), 0.30, 0.95))


def m2_graph_metrics(graph: nx.Graph) -> dict[str, dict[str, float]]:
    """M2: Graph analytics — betweenness, PageRank, bottleneck score.
    Returns {facility_id: {betweenness_centrality, pagerank, bottleneck_score}}.
    composite_bottleneck_score = 0.6 × norm_betweenness + 0.4 × norm_pagerank.
    """
    if len(graph.nodes) == 0:
        return {}

    betweenness = nx.betweenness_centrality(graph, normalized=True)
    pagerank = nx.pagerank(graph, alpha=0.85)

    max_b = max(betweenness.values()) or 1.0
    max_p = max(pagerank.values()) or 1.0

    result = {}
    for node in graph.nodes:
        norm_b = betweenness[node] / max_b
        norm_p = pagerank[node] / max_p
        result[node] = {
            "betweenness_centrality": float(betweenness[node]),
            "pagerank": float(pagerank[node]),
            "bottleneck_score": float(np.clip(0.6 * norm_b + 0.4 * norm_p, 0.0, 1.0)),
        }
    return result


def m4_optimal_route(
    graph: nx.Graph,
    source: str,
    candidates: list[str],
    facility_states: dict[str, FacilityState],
) -> list[dict[str, Any]]:
    """M4: Optimal referral router via Dijkstra + composite edge weight.
    Returns routes sorted by estimated_tat ascending.
    estimated_tat = path travel time (hours) + destination TAT (hours).
    """
    routes = []
    for target in candidates:
        if target == source or target not in graph.nodes or source not in graph.nodes:
            continue
        try:
            path = nx.dijkstra_path(graph, source, target, weight="weight")
            travel_min = sum(
                graph[path[i]][path[i + 1]].get("weight", 30)
                for i in range(len(path) - 1)
            )
            dest_tat = facility_states.get(target, FacilityState()).tat_hours
            routes.append({
                "facility_id": target,
                "path": path,
                "estimated_tat": float(travel_min / 60.0 + dest_tat),
            })
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            continue

    return sorted(routes, key=lambda r: r["estimated_tat"])


# ─── Status computation ───────────────────────────────────────────────────────

# Resources where "below" thresholds only apply if the facility actually uses them.
# A CBNAAT hub has truenat_chips=0 in baseline and should never go critical for chips.
_STOCK_RESOURCES = frozenset({"truenat_chips", "cartridges"})


def _compute_status(
    fs: FacilityState,
    baseline: FacilityState | None = None,
) -> str:
    """Return facility status (ok/warning/critical/offline).

    baseline is used to skip "below" thresholds for resources the facility
    never had (e.g. truenat_chips=0 on a CBNAAT hub).
    """
    if fs.machines == 0:
        return "offline"

    def _skip_below(field_name: str) -> bool:
        """True if this facility doesn't use this resource (baseline value = 0)."""
        return (
            field_name in _STOCK_RESOURCES
            and baseline is not None
            and getattr(baseline, field_name, 0) == 0
        )

    for field_name, (direction, threshold) in _CRITICAL.items():
        if direction == "below" and _skip_below(field_name):
            continue
        value = getattr(fs, field_name, None)
        if value is None:
            continue
        if direction == "above" and value > threshold:
            return "critical"
        if direction == "below" and value < threshold:
            return "critical"

    for field_name, (direction, threshold) in _WARN.items():
        if direction == "below" and _skip_below(field_name):
            continue
        value = getattr(fs, field_name, None)
        if value is None:
            continue
        if direction == "above" and value > threshold:
            return "warning"
        if direction == "below" and value < threshold:
            return "warning"

    return "ok"


# ─── ScenarioGenerator ───────────────────────────────────────────────────────

class ScenarioGenerator:
    """Runs one scenario and produces FlatTickSnapshot rows for all ticks.

    Usage::

        gen = ScenarioGenerator(scenario_config, networks_data, seed=42)
        snapshots = gen.run()   # list[FlatTickSnapshot] — one dict per tick×facility
    """

    def __init__(
        self,
        scenario: ScenarioConfig,
        networks_data: dict,
        seed: int = 42,
    ) -> None:
        self.scenario = scenario
        self.networks_data = networks_data
        self.rng = np.random.default_rng(seed)
        # Cache: network_id -> facility_id -> baseline FacilityState
        self._baselines: dict[str, dict[str, FacilityState]] = {}
        # Cache: network_id -> NetworkX graph (built once, used for layout)
        self._graphs: dict[str, nx.Graph] = {}
        # Cache: facility_id -> network_id (reverse lookup)
        self._fac_to_net: dict[str, str] = {}
        # Cache: network_id -> inter-network overflow targets {source_fac: target_net}
        self._overflow_routes: dict[str, str] = {}  # source_facility -> target_net_id
        self._init_caches()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init_caches(self) -> None:
        for net_id, net_data in self.networks_data["networks"].items():
            self._baselines[net_id] = {}
            self._graphs[net_id] = build_network_graph(net_data)
            for fac_id, fac_data in net_data["facilities"].items():
                self._fac_to_net[fac_id] = net_id
                b = fac_data["baseline"]
                self._baselines[net_id][fac_id] = FacilityState(
                    patients_queued=float(b.get("patients_queued", 0)),
                    cartridges=float(b.get("cartridges", 0)),
                    truenat_chips=float(b.get("truenat_chips", 0)),
                    travel_time_min=float(b.get("travel_time_min", 0)),
                    tat_hours=float(b.get("tat_hours", 0)),
                    hr_on_shift=float(b.get("hr_on_shift", 0)),
                    machines=int(b.get("machines", 0)),
                    modules=int(b.get("modules", 0)),
                    samples_per_module_per_day=float(b.get("samples_per_module_per_day", 0)),
                    daily_consumption=float(b.get("daily_consumption", 0)),
                    smear_positivity_rate=float(b.get("smear_positivity_rate", 0)),
                    specimen_rejection_rate=float(b.get("specimen_rejection_rate", 0)),
                    referral_completion_rate=float(b.get("referral_completion_rate", 0)),
                    chw_available=int(b.get("chw_available", 0)),
                    bayesian_stockout_prob=float(b.get("bayesian_stockout_prob", 0)),
                    cascade_dropout_risk=float(b.get("cascade_dropout_risk", 0)),
                    status=str(b.get("status", "ok")),
                )
        # Build overflow routes from inter_network_links
        for link in self.networks_data.get("inter_network_links", []):
            if link.get("flow_type") == "overflow":
                self._overflow_routes[link["source_facility"]] = link["target"]

    def _init_global_state(self) -> GlobalGenState:
        """Seed GlobalGenState from network baselines (or SC-08 initial_states)."""
        networks: dict[str, NetworkGenState] = {}
        for net_id, net_data in self.networks_data["networks"].items():
            facilities: dict[str, FacilityState] = {}
            for fac_id in net_data["facilities"]:
                fs = copy.deepcopy(self._baselines[net_id][fac_id])
                # SC-08: override with post-crisis initial_states if specified
                if self.scenario.initial_states:
                    overrides = (
                        self.scenario.initial_states
                        .get(net_id, {})
                        .get(fac_id, {})
                    )
                    for field_name, value in overrides.items():
                        if hasattr(fs, field_name):
                            setattr(fs, field_name, type(getattr(fs, field_name))(value))
                facilities[fac_id] = fs
            networks[net_id] = NetworkGenState(
                network_id=net_id,
                facilities=facilities,
                graph=self._graphs[net_id],
            )
        return GlobalGenState(networks=networks, overflow_pending={}, tick=0)

    # ── Tick logic ────────────────────────────────────────────────────────────

    def _tick(self, state: GlobalGenState, tick: int) -> GlobalGenState:
        """Produce a NEW GlobalGenState for the given tick. Never mutates input."""
        new_state = copy.deepcopy(state)
        new_state.tick = tick
        new_state.fired_alerts = []

        # 1. Apply deltas — switch to post_event_deltas after event_activation_tick
        use_post = (
            self.scenario.event_activation_tick is not None
            and tick >= self.scenario.event_activation_tick
            and self.scenario.post_event_deltas
        )
        active_deltas = (
            self.scenario.post_event_deltas
            if use_post
            else self.scenario.per_tick_deltas
        )

        for fac_id, deltas in active_deltas.items():
            net_id = self._fac_to_net.get(fac_id)
            if net_id is None or net_id not in new_state.networks:
                continue
            fs = new_state.networks[net_id].facilities.get(fac_id)
            if fs is None:
                continue
            for field_name, delta in deltas.items():
                noise = float(self.rng.normal(0, max(0.05 * abs(delta), 1e-6)))
                raw = getattr(fs, field_name, 0.0) + delta + noise
                if field_name in _RATE_FIELDS:
                    raw = float(np.clip(raw, 0.0, 1.0))
                elif field_name in _COUNT_FIELDS:
                    raw = max(0.0, float(raw))
                elif field_name in _INT_FIELDS:
                    raw = max(0, int(round(raw)))
                setattr(fs, field_name, raw)

        # 2. Update B1 and status for all facilities
        for net_id, net_state in new_state.networks.items():
            for fac_id, fs in net_state.facilities.items():
                baseline = self._baselines[net_id][fac_id]
                if baseline.daily_consumption > 0:
                    fs.bayesian_stockout_prob = b1_stockout_prob(fs, self.rng)
                fs.status = _compute_status(fs, baseline)

        # 3. Check for overflow conditions and accumulate
        for fac_id, target_net in self._overflow_routes.items():
            net_id = self._fac_to_net.get(fac_id)
            if net_id is None:
                continue
            fs = new_state.networks[net_id].facilities.get(fac_id)
            if fs is None:
                continue
            if fs.patients_queued > _CRITICAL["patients_queued"][1]:
                excess = fs.patients_queued - _CRITICAL["patients_queued"][1]
                overflow_amount = excess * 0.3  # 30% of excess overflows
                new_state.overflow_pending[target_net] = (
                    new_state.overflow_pending.get(target_net, 0.0) + overflow_amount
                )

        # 4. Apply accumulated overflow to target hubs
        self.apply_overflow(new_state)

        # 5. Fire scripted alerts for this tick
        for alert_cfg in self.scenario.alerts:
            if alert_cfg.tick != tick:
                continue
            net_id = self._fac_to_net.get(alert_cfg.facility)
            if net_id is None:
                continue
            fs = new_state.networks[net_id].facilities.get(alert_cfg.facility)
            if fs is None:
                continue
            msg = safe_format(alert_cfg.msg, fs.__dict__)
            shap = generate_alert_shap(alert_cfg, fs, self.scenario)
            new_state.fired_alerts.append(AlertRecord(
                tick=tick,
                facility_id=alert_cfg.facility,
                network_id=net_id,
                alert_type=alert_cfg.type,
                message=msg,
                shap_contributions=shap,
                severity=alert_cfg.severity,
            ))

        return new_state

    @staticmethod
    def apply_overflow(state: GlobalGenState) -> None:
        """Distribute overflow_pending into target network hubs (in-place on new_state)."""
        for target_net_id, overflow_amount in list(state.overflow_pending.items()):
            if overflow_amount <= 0 or target_net_id not in state.networks:
                continue
            net_state = state.networks[target_net_id]
            # Find the hub facility (type == "hub") and add overflow
            for fac_id, fs in net_state.facilities.items():
                # Hubs identified by having machines > 0 or modules > 0
                if fs.machines > 0 or fs.modules > 0:
                    fs.patients_queued = max(0.0, fs.patients_queued + overflow_amount)
                    break
        state.overflow_pending.clear()

    # ── Snapshot serialisation ────────────────────────────────────────────────

    def _state_to_snapshots(
        self,
        state: GlobalGenState,
        tick: int,
    ) -> list[FlatTickSnapshot]:
        """Convert one GlobalGenState to FlatTickSnapshot dicts for all facilities."""
        snapshots: list[FlatTickSnapshot] = []
        for net_id, net_state in state.networks.items():
            gm = m2_graph_metrics(net_state.graph)
            for fac_id, fs in net_state.facilities.items():
                metrics = gm.get(fac_id, {})
                stock = fs.cartridges if fs.cartridges > 0 else fs.truenat_chips
                eff_days = (
                    stock / fs.daily_consumption
                    if fs.daily_consumption > 0 and stock > 0
                    else 0.0
                )
                pred_stockout = float(tick + eff_days) if eff_days > 0 else float("nan")
                snapshots.append({
                    "tick": tick,
                    "facility_id": fac_id,
                    "network_id": net_id,
                    "patients_queued": float(fs.patients_queued),
                    "cartridges": float(fs.cartridges),
                    "truenat_chips": float(fs.truenat_chips),
                    "travel_time_min": float(fs.travel_time_min),
                    "tat_hours": float(fs.tat_hours),
                    "hr_on_shift": float(fs.hr_on_shift),
                    "machines": int(fs.machines),
                    "modules": int(fs.modules),
                    "samples_per_module_per_day": float(fs.samples_per_module_per_day),
                    "daily_consumption": float(fs.daily_consumption),
                    "smear_positivity_rate": float(fs.smear_positivity_rate),
                    "specimen_rejection_rate": float(fs.specimen_rejection_rate),
                    "referral_completion_rate": float(fs.referral_completion_rate),
                    "chw_available": int(fs.chw_available),
                    "bayesian_stockout_prob": float(fs.bayesian_stockout_prob),
                    "cascade_dropout_risk": float(fs.cascade_dropout_risk),
                    "status": str(fs.status),
                    "betweenness_centrality": float(metrics.get("betweenness_centrality", 0.0)),
                    "pagerank": float(metrics.get("pagerank", 0.0)),
                    "bottleneck_score": float(metrics.get("bottleneck_score", 0.0)),
                    "effective_capacity_days": float(eff_days),
                    "predicted_stockout_day": pred_stockout,
                })
        return snapshots

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> list[FlatTickSnapshot]:
        """Run all ticks and return flattened list of FlatTickSnapshot dicts."""
        state = self._init_global_state()
        snapshots: list[FlatTickSnapshot] = []
        for tick in range(self.scenario.max_ticks):
            state = self._tick(state, tick)
            snapshots.extend(self._state_to_snapshots(state, tick))
        return snapshots

    def run_with_alerts(self) -> tuple[list[FlatTickSnapshot], list[AlertRecord]]:
        """Run all ticks, return (snapshots, all_alerts)."""
        state = self._init_global_state()
        snapshots: list[FlatTickSnapshot] = []
        alerts: list[AlertRecord] = []
        for tick in range(self.scenario.max_ticks):
            state = self._tick(state, tick)
            snapshots.extend(self._state_to_snapshots(state, tick))
            alerts.extend(state.fired_alerts)
        return snapshots, alerts

    def _find_network(self, facility_id: str) -> str | None:
        return self._fac_to_net.get(facility_id)
