"""Tests for viz/network_map.py — stateless Plotly figure builders."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest
import yaml

from core.models import FlatTickSnapshot
from core.network_layout import load_network_layout, load_network_links
from viz.network_map import (
    STATUS_COLORS,
    NODE_SIZES,
    build_mini_map,
    build_network_figure,
)

NETWORKS_PATH = Path("config/networks.yaml")


@pytest.fixture(scope="module")
def networks_data() -> dict:
    return yaml.safe_load(NETWORKS_PATH.read_text())


@pytest.fixture(scope="module")
def net_a_layout(networks_data) -> dict:
    return load_network_layout(networks_data, "NET-A")


@pytest.fixture(scope="module")
def net_a_links(networks_data) -> list:
    return load_network_links(networks_data, "NET-A")


@pytest.fixture(scope="module")
def sample_tick_df() -> pd.DataFrame:
    """Load SC-01 tick 0 from pre-generated parquet."""
    df = pd.read_parquet("data/scenarios/sc-01.parquet")
    return df[df["tick"] == 0].reset_index(drop=True)


# ─── load_network_layout ─────────────────────────────────────────────────────

def test_layout_has_14_facilities_for_net_a(net_a_layout):
    assert len(net_a_layout) == 14


def test_layout_facility_has_required_keys(net_a_layout):
    for fac_id, lay in net_a_layout.items():
        assert "display_name" in lay
        assert "type" in lay
        assert "x" in lay
        assert "y" in lay


def test_layout_dhc_a_is_hub(net_a_layout):
    assert net_a_layout["DHC-A"]["type"] == "hub"


def test_layout_positions_in_unit_range(net_a_layout):
    for fac_id, lay in net_a_layout.items():
        assert 0.0 <= lay["x"] <= 1.0, f"{fac_id}: x out of range"
        assert 0.0 <= lay["y"] <= 1.0, f"{fac_id}: y out of range"


# ─── build_network_figure — basic ────────────────────────────────────────────

def test_build_network_figure_returns_go_figure(
    sample_tick_df, net_a_layout, net_a_links
):
    fig = build_network_figure(sample_tick_df, 0, "NET-A", net_a_layout, net_a_links)
    assert isinstance(fig, go.Figure)


def test_build_network_figure_empty_df_returns_empty_figure(
    net_a_layout, net_a_links
):
    empty_df = pd.DataFrame()
    fig = build_network_figure(empty_df, 0, "NET-A", net_a_layout, net_a_links)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_network_figure_has_node_trace(
    sample_tick_df, net_a_layout, net_a_links
):
    fig = build_network_figure(sample_tick_df, 0, "NET-A", net_a_layout, net_a_links)
    # At least one trace with mode containing "markers"
    marker_traces = [t for t in fig.data if "markers" in (t.mode or "")]
    assert len(marker_traces) >= 1


def test_build_network_figure_node_count(
    sample_tick_df, net_a_layout, net_a_links
):
    """The main node trace should have 14 nodes (NET-A facility count)."""
    fig = build_network_figure(sample_tick_df, 0, "NET-A", net_a_layout, net_a_links)
    # Node trace is the last markers+text trace
    node_traces = [t for t in fig.data if t.mode == "markers+text"]
    assert len(node_traces) == 1
    assert len(node_traces[0].x) == 14


def test_build_network_figure_node_sizes(
    sample_tick_df, net_a_layout, net_a_links
):
    """Hub nodes should have size 30, CHC nodes size 12."""
    fig = build_network_figure(sample_tick_df, 0, "NET-A", net_a_layout, net_a_links)
    node_trace = [t for t in fig.data if t.mode == "markers+text"][0]
    text_labels = list(node_trace.text)

    dhc_idx = text_labels.index("DHC-A")
    chc_idx = text_labels.index("CHC1-A")

    sizes = list(node_trace.marker.size)
    assert sizes[dhc_idx] == NODE_SIZES["hub"]    # 30
    assert sizes[chc_idx] == NODE_SIZES["chc"]    # 12


def test_build_network_figure_has_edge_traces(
    sample_tick_df, net_a_layout, net_a_links
):
    """Line traces should exist for edges."""
    fig = build_network_figure(sample_tick_df, 0, "NET-A", net_a_layout, net_a_links)
    line_traces = [t for t in fig.data if t.mode == "lines"]
    assert len(line_traces) >= 1


def test_build_network_figure_reroute_creates_blue_dashed_trace(
    sample_tick_df, net_a_layout, net_a_links
):
    """Active reroutes should produce a blue dashed edge trace."""
    fig = build_network_figure(
        sample_tick_df, 7, "NET-A", net_a_layout, net_a_links,
        active_reroutes=[["MC2-A", "TL2-A"]],
    )
    blue_traces = [
        t for t in fig.data
        if t.mode == "lines" and t.line.color == "#3b82f6"
    ]
    assert len(blue_traces) >= 1


def test_build_network_figure_critical_node_outer_ring(
    net_a_layout, net_a_links, networks_data
):
    """Critical nodes should produce an outer ring trace."""
    df = pd.read_parquet("data/scenarios/sc-01.parquet")
    # Find a tick where DHC-A is critical (late ticks in SC-01)
    critical_rows = df[(df["facility_id"] == "DHC-A") & (df["status"] == "critical")]
    if critical_rows.empty:
        pytest.skip("No critical ticks in SC-01 for DHC-A")

    tick = int(critical_rows["tick"].iloc[0])
    tick_df = df[df["tick"] == tick]
    fig = build_network_figure(tick_df, tick, "NET-A", net_a_layout, net_a_links)

    # Outer ring: markers-only trace (no text) added before the node trace
    ring_traces = [
        t for t in fig.data
        if t.mode == "markers" and not hasattr(t, "text")
        or (t.mode == "markers" and (t.text is None or len(t.text) == 0))
    ]
    assert len(ring_traces) >= 1


def test_build_network_figure_selected_facility_highlighted(
    sample_tick_df, net_a_layout, net_a_links
):
    """Selected facility should have a white outline (line color #ffffff)."""
    fig = build_network_figure(
        sample_tick_df, 0, "NET-A", net_a_layout, net_a_links,
        selected_facility="DHC-A",
    )
    node_trace = [t for t in fig.data if t.mode == "markers+text"][0]
    text_labels = list(node_trace.text)
    dhc_idx = text_labels.index("DHC-A")

    line_colors = list(node_trace.marker.line.color)
    assert line_colors[dhc_idx] == "#ffffff"


def test_build_network_figure_hover_text_present(
    sample_tick_df, net_a_layout, net_a_links
):
    """Node hover text should contain facility display_name."""
    fig = build_network_figure(sample_tick_df, 0, "NET-A", net_a_layout, net_a_links)
    node_trace = [t for t in fig.data if t.mode == "markers+text"][0]
    hover_texts = list(node_trace.hovertext)
    assert any("District Hospital Chandrapur" in h for h in hover_texts)


def test_build_network_figure_title_contains_network_and_tick(
    sample_tick_df, net_a_layout, net_a_links
):
    fig = build_network_figure(sample_tick_df, 5, "NET-A", net_a_layout, net_a_links)
    title = fig.layout.title.text
    assert "NET-A" in title
    assert "5" in title


# ─── build_mini_map ───────────────────────────────────────────────────────────

def test_build_mini_map_returns_go_figure(
    sample_tick_df, net_a_layout
):
    fig = build_mini_map(sample_tick_df, 0, "NET-A", net_a_layout)
    assert isinstance(fig, go.Figure)


def test_build_mini_map_empty_df_returns_empty_figure(net_a_layout):
    fig = build_mini_map(pd.DataFrame(), 0, "NET-A", net_a_layout)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_mini_map_dimensions(sample_tick_df, net_a_layout):
    fig = build_mini_map(sample_tick_df, 0, "NET-A", net_a_layout)
    assert fig.layout.width == 200
    assert fig.layout.height == 200


def test_build_mini_map_no_tooltips(sample_tick_df, net_a_layout):
    """Mini-map nodes should have hoverinfo='skip'."""
    fig = build_mini_map(sample_tick_df, 0, "NET-A", net_a_layout)
    assert len(fig.data) == 1
    assert fig.data[0].hoverinfo == "skip"


def test_build_mini_map_no_text_labels(sample_tick_df, net_a_layout):
    """Mini-map should use markers only (no text labels)."""
    fig = build_mini_map(sample_tick_df, 0, "NET-A", net_a_layout)
    assert fig.data[0].mode == "markers"


def test_build_mini_map_14_nodes_for_net_a(sample_tick_df, net_a_layout):
    fig = build_mini_map(sample_tick_df, 0, "NET-A", net_a_layout)
    assert len(fig.data[0].x) == 14


# ─── Status colour mapping ────────────────────────────────────────────────────

def test_status_colors_defined():
    assert STATUS_COLORS["ok"] == "#22c55e"
    assert STATUS_COLORS["warning"] == "#f59e0b"
    assert STATUS_COLORS["critical"] == "#ef4444"
    assert "offline" in STATUS_COLORS


def test_node_sizes_defined():
    assert NODE_SIZES["hub"] == 30
    assert NODE_SIZES["truenat"] == 22
    assert NODE_SIZES["microscopy"] == 16
    assert NODE_SIZES["chc"] == 12
