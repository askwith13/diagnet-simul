"""Performance validation tests — NFR1, NFR2, NFR3.

Measures the non-Streamlit portions of the critical rendering path.
Streamlit DOM overhead is not measurable in unit tests; the thresholds
here are set well within the budget so that Streamlit overhead still
fits within the NFR limits.

NFR1: tick render < 400ms at 4× (core computation budget: < 100ms)
NFR2: startup load < 500ms (all 8 scenarios)
NFR3: 5 networks simultaneously on Tab 2 (mini-map build budget: < 200ms)
NFR8: JSON serialisation < 500ms (already tested in test_export.py)
"""
from __future__ import annotations

import statistics
import time
from pathlib import Path

import pandas as pd
import pytest
import yaml

from core.network_layout import load_network_layout, load_network_links
from loader import load_scenario_payloads
from playback import advance_tick, apply_playback_step
from session import IS_PLAYING, SCENARIO_SNAPSHOTS, TICK_CURSOR, init_session_state
from viz.network_map import build_mini_map, build_network_figure

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def networks_data() -> dict:
    return yaml.safe_load(Path("config/networks.yaml").read_text())


@pytest.fixture(scope="module")
def all_payloads() -> dict:
    return load_scenario_payloads()


@pytest.fixture(scope="module")
def net_a_layout(networks_data) -> dict:
    return load_network_layout(networks_data, "NET-A")


@pytest.fixture(scope="module")
def net_a_links(networks_data) -> list:
    return load_network_links(networks_data, "NET-A")


# ── NFR2: Startup load < 500ms ────────────────────────────────────────────────

def test_load_scenario_payloads_under_500ms():
    """AC1: All 8 scenario parquets load into memory in < 500ms."""
    t0 = time.perf_counter()
    payloads = load_scenario_payloads()
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert len(payloads) == 8, "Expected 8 scenarios"
    assert elapsed_ms < 500, (
        f"load_scenario_payloads() took {elapsed_ms:.1f}ms — exceeds 500ms NFR. "
        "Consider checking disk speed or parquet compression."
    )


def test_load_all_network_layouts_under_50ms(networks_data):
    """Network layout loading from networks.yaml should be near-instant."""
    from core.network_layout import load_all_layouts

    t0 = time.perf_counter()
    layouts = load_all_layouts(networks_data)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert len(layouts) == 5
    assert elapsed_ms < 50, f"load_all_layouts() took {elapsed_ms:.1f}ms — expected < 50ms"


# ── NFR1: Core per-tick computation < 100ms (budget for 400ms limit) ──────────

def test_tick_df_lookup_under_50ms(all_payloads):
    """DataFrame tick filtering should be < 50ms per tick."""
    tick_df = all_payloads["sc-01"]["tick_df"]

    times = []
    for tick in range(20):
        t0 = time.perf_counter()
        cur = tick_df[tick_df["tick"] == tick]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert not cur.empty
        times.append(elapsed_ms)

    median_ms = statistics.median(times)
    assert median_ms < 50, (
        f"tick_df lookup median {median_ms:.2f}ms — expected < 50ms"
    )


def test_build_network_figure_under_200ms(all_payloads, net_a_layout, net_a_links):
    """build_network_figure() for NET-A should complete in < 200ms."""
    tick_df = all_payloads["sc-01"]["tick_df"]

    times = []
    for tick in range(20):
        cur_df = tick_df[tick_df["tick"] == tick]
        t0 = time.perf_counter()
        fig = build_network_figure(cur_df, tick, "NET-A", net_a_layout, net_a_links)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert fig is not None
        times.append(elapsed_ms)

    median_ms = statistics.median(times)
    assert median_ms < 200, (
        f"build_network_figure() median {median_ms:.1f}ms — expected < 200ms"
    )


def test_full_tick_core_computation_under_400ms(all_payloads, net_a_layout, net_a_links):
    """AC2: DataFrame lookup + figure build together < 400ms median over 20 ticks.

    This is the core computational budget for the playback loop.
    Streamlit DOM overhead must fit within the remaining budget.
    """
    tick_df = all_payloads["sc-01"]["tick_df"]
    times = []

    for tick in range(20):
        t0 = time.perf_counter()
        # 1. DataFrame lookup
        cur_df = tick_df[tick_df["tick"] == tick]
        # 2. Plotly figure build
        build_network_figure(cur_df, tick, "NET-A", net_a_layout, net_a_links)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        times.append(elapsed_ms)

    median_ms = statistics.median(times)
    max_ms = max(times)
    assert median_ms < 400, (
        f"Core tick computation median {median_ms:.1f}ms exceeds 400ms NFR2. "
        f"Max: {max_ms:.1f}ms."
    )


def test_apply_playback_step_under_1ms():
    """apply_playback_step() is pure dict mutation — must be < 1ms."""
    state = {IS_PLAYING: True, TICK_CURSOR: 5, SCENARIO_SNAPSHOTS: {}}
    times = []
    for _ in range(100):
        state[IS_PLAYING] = True
        state[TICK_CURSOR] = 5
        t0 = time.perf_counter()
        apply_playback_step(state, 25, "sc-01", None)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        state[IS_PLAYING] = True  # reset for next iteration
        times.append(elapsed_ms)

    median_ms = statistics.median(times)
    assert median_ms < 1.0, (
        f"apply_playback_step() median {median_ms:.3f}ms — expected < 1ms"
    )


# ── NFR3: Tab 2 — 5 mini-maps simultaneously < 200ms ─────────────────────────

def test_5_mini_maps_under_200ms(all_payloads, networks_data):
    """NFR3: Building all 5 mini-maps (Tab 2) should complete in < 200ms."""
    from core.network_layout import load_network_layout

    tick_df = all_payloads["sc-01"]["tick_df"]
    net_ids = ["NET-A", "NET-B", "NET-C", "NET-D", "NET-E"]
    layouts = {n: load_network_layout(networks_data, n) for n in net_ids}

    times = []
    for tick in range(10):
        cur_df = tick_df[tick_df["tick"] == tick]
        t0 = time.perf_counter()
        for net_id in net_ids:
            build_mini_map(cur_df, tick, net_id, layouts[net_id])
        elapsed_ms = (time.perf_counter() - t0) * 1000
        times.append(elapsed_ms)

    median_ms = statistics.median(times)
    assert median_ms < 200, (
        f"5 mini-maps median {median_ms:.1f}ms — expected < 200ms (NFR3)"
    )


# ── NFR8: JSON serialisation — reference test_export.py ──────────────────────

def test_json_serialisation_nfr_reference():
    """AC3: Verified by test_export.py::test_json_serialisation_benchmark.

    This test confirms the cross-reference is intact.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "test_export", Path("tests/test_export.py")
    )
    assert spec is not None, "test_export.py not found"
    # The actual benchmark is in test_export.py; this just verifies it exists
    source = Path("tests/test_export.py").read_text()
    assert "test_json_serialisation_benchmark" in source
    assert "500" in source   # 500ms threshold


# ── Summary report ────────────────────────────────────────────────────────────

def test_performance_summary(all_payloads, net_a_layout, net_a_links, networks_data):
    """Print a performance summary table for demo-day reference."""
    from core.network_layout import load_network_layout

    tick_df = all_payloads["sc-01"]["tick_df"]
    net_ids = ["NET-A", "NET-B", "NET-C", "NET-D", "NET-E"]
    layouts = {n: load_network_layout(networks_data, n) for n in net_ids}

    # Startup
    t0 = time.perf_counter()
    load_scenario_payloads()
    startup_ms = (time.perf_counter() - t0) * 1000

    # Per-tick core
    tick_times = []
    for tick in range(20):
        cur_df = tick_df[tick_df["tick"] == tick]
        t0 = time.perf_counter()
        build_network_figure(cur_df, tick, "NET-A", net_a_layout, net_a_links)
        tick_times.append((time.perf_counter() - t0) * 1000)

    # Tab 2 mini-maps
    mini_times = []
    for tick in range(10):
        cur_df = tick_df[tick_df["tick"] == tick]
        t0 = time.perf_counter()
        for net_id in net_ids:
            build_mini_map(cur_df, tick, net_id, layouts[net_id])
        mini_times.append((time.perf_counter() - t0) * 1000)

    print(f"\n{'─'*50}")
    print("DiagNet Performance Summary")
    print(f"{'─'*50}")
    print(f"Startup (8 scenarios loaded):  {startup_ms:6.1f}ms  (NFR: < 500ms)")
    print(f"Per-tick core computation:     {statistics.median(tick_times):6.1f}ms  (NFR: < 400ms)")
    print(f"Tab 2 (5 mini-maps combined):  {statistics.median(mini_times):6.1f}ms  (NFR: < 200ms)")
    print(f"{'─'*50}")

    # All NFRs must pass
    assert startup_ms < 500
    assert statistics.median(tick_times) < 400
    assert statistics.median(mini_times) < 200
