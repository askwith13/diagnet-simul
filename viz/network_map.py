"""Stateless Plotly network map builders.

All functions are pure: (data, layout, options) → go.Figure.
No session_state reads or writes. No generation/ imports.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from core.models import FacilityLayout

# ─── Constants ───────────────────────────────────────────────────────────────

NODE_SIZES: dict[str, int] = {
    "hub": 30,
    "truenat": 22,
    "microscopy": 16,
    "chc": 12,
}
STATUS_COLORS: dict[str, str] = {
    "ok": "#22c55e",
    "warning": "#f59e0b",
    "critical": "#ef4444",
    "offline": "#808080",
}
# Edge colour/dash by worst-endpoint status
EDGE_STYLES: dict[str, dict] = {
    "ok":       {"color": "#22c55e", "dash": "solid", "width": 1.5},
    "warning":  {"color": "#f59e0b", "dash": "solid", "width": 2.0},
    "critical": {"color": "#ef4444", "dash": "dash",  "width": 2.0},
    "reroute":  {"color": "#3b82f6", "dash": "dash",  "width": 2.5},
}
OUTER_RING_OPACITY = 0.4
OUTER_RING_SCALE = 1.5

# Metrics to show in hover tooltip (ordered)
_HOVER_METRICS = [
    ("patients_queued",       "Patients queued",     ".0f"),
    ("cartridges",            "Cartridges",          ".0f"),
    ("truenat_chips",         "Truenat chips",       ".0f"),
    ("tat_hours",             "TAT",                 ".1f"),
    ("bayesian_stockout_prob","P(stockout 14d)",     ".2f"),
    ("cascade_dropout_risk",  "Cascade risk",        ".2f"),
    ("bottleneck_score",      "Bottleneck score",    ".2f"),
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _facility_row(tick_df: pd.DataFrame, facility_id: str) -> dict | None:
    """Return the row dict for facility_id, or None if absent."""
    rows = tick_df[tick_df["facility_id"] == facility_id]
    if rows.empty:
        return None
    return rows.iloc[0].to_dict()


def _edge_style(status_a: str, status_b: str) -> dict:
    """Determine edge style from the worse of two endpoint statuses.
    Offline is treated as critical for edge colouring purposes.
    """
    priority = ["critical", "offline", "warning", "ok"]
    for worst in priority:
        if worst in (status_a, status_b):
            # "offline" maps to the same visual style as "critical"
            return EDGE_STYLES.get(worst, EDGE_STYLES["critical"])
    return EDGE_STYLES["ok"]


def _build_hover_text(facility_id: str, layout: FacilityLayout, row: dict) -> str:
    """Build HTML hover tooltip for one facility."""
    lines = [
        f"<b>{layout['display_name']}</b>",
        f"Status: <b>{row.get('status','ok').upper()}</b>",
    ]
    for field, label, fmt in _HOVER_METRICS:
        val = row.get(field)
        if val is not None and val != 0.0:
            try:
                lines.append(f"{label}: {val:{fmt}}")
            except (ValueError, TypeError):
                pass
    return "<br>".join(lines)


# ─── Public API ───────────────────────────────────────────────────────────────

def build_network_figure(
    tick_df: pd.DataFrame,
    tick: int,
    network_id: str,
    layout: dict[str, FacilityLayout],
    links: list[list],
    selected_facility: str | None = None,
    active_reroutes: list[list[str]] | None = None,
) -> go.Figure:
    """Build the full Tab 1 network map figure for one network at one tick.

    Args:
        tick_df: All FlatTickSnapshot rows for this tick (all networks; filtered here).
        tick: Current tick index.
        network_id: Which network to render.
        layout: {facility_id: FacilityLayout} from load_network_layout().
        links: [[src, dst, travel_time_min], ...] from load_network_links().
        selected_facility: Highlighted node (outlined in white).
        active_reroutes: [[from, to], ...] drawn as blue dashed edges.

    Returns:
        go.Figure — empty figure if tick_df is empty or has no matching rows.
    """
    if tick_df.empty or layout is None:
        return go.Figure()

    net_df = tick_df[tick_df["network_id"] == network_id]
    if net_df.empty:
        return go.Figure()

    reroute_set: set[tuple[str, str]] = set()
    if active_reroutes:
        for pair in active_reroutes:
            if len(pair) >= 2:
                reroute_set.add((pair[0], pair[1]))
                reroute_set.add((pair[1], pair[0]))  # undirected display

    traces: list[go.BaseTraceType] = []

    # ── 1. Edge traces ────────────────────────────────────────────────────────
    fac_status: dict[str, str] = {}
    for fac_id in layout:
        row = _facility_row(net_df, fac_id)
        fac_status[fac_id] = row["status"] if row else "ok"

    # ── 1a. Reroute edges (drawn first; may not exist in topology) ─────────────
    reroute_xs: list[float] = []
    reroute_ys: list[float] = []
    if active_reroutes:
        for pair in active_reroutes:
            if len(pair) < 2:
                continue
            src, dst = str(pair[0]), str(pair[1])
            if src not in layout or dst not in layout:
                continue
            reroute_xs += [layout[src]["x"], layout[dst]["x"], None]
            reroute_ys += [layout[src]["y"], layout[dst]["y"], None]

    if reroute_xs:
        style = EDGE_STYLES["reroute"]
        traces.append(go.Scatter(
            x=reroute_xs, y=reroute_ys,
            mode="lines",
            line=dict(color=style["color"], dash=style["dash"], width=style["width"]),
            hoverinfo="skip",
            showlegend=False,
        ))

    # ── 1b. Regular topology edges ─────────────────────────────────────────────
    edge_groups: dict[str, tuple[list[float], list[float]]] = {
        "ok": ([], []),
        "warning": ([], []),
        "critical": ([], []),
    }
    for link in links:
        if len(link) < 2:
            continue
        src, dst = str(link[0]), str(link[1])
        if src not in layout or dst not in layout:
            continue
        # Skip links that are reroutes (already drawn above)
        if (src, dst) in reroute_set or (dst, src) in reroute_set:
            continue
        lx, ly = layout[src]["x"], layout[src]["y"]
        rx, ry = layout[dst]["x"], layout[dst]["y"]

        colour = _edge_style(fac_status.get(src, "ok"), fac_status.get(dst, "ok"))["color"]
        key = {
            "#22c55e": "ok",
            "#f59e0b": "warning",
            "#ef4444": "critical",
        }.get(colour, "ok")

        xs, ys = edge_groups[key]
        xs += [lx, rx, None]
        ys += [ly, ry, None]

    for key, (xs, ys) in edge_groups.items():
        if not xs:
            continue
        style = EDGE_STYLES[key]
        traces.append(go.Scatter(
            x=xs, y=ys,
            mode="lines",
            line=dict(color=style["color"], dash=style["dash"], width=style["width"]),
            hoverinfo="skip",
            showlegend=False,
        ))

    # ── 2. Outer-ring trace for critical nodes ─────────────────────────────────
    ring_x, ring_y, ring_sizes, ring_colors = [], [], [], []
    for fac_id, lay in layout.items():
        if fac_status.get(fac_id) == "critical":
            ring_x.append(lay["x"])
            ring_y.append(lay["y"])
            base_size = NODE_SIZES.get(lay["type"], 12)
            ring_sizes.append(int(base_size * OUTER_RING_SCALE))
            ring_colors.append(STATUS_COLORS["critical"])

    if ring_x:
        traces.append(go.Scatter(
            x=ring_x, y=ring_y,
            mode="markers",
            marker=dict(
                size=ring_sizes,
                color=ring_colors,
                opacity=OUTER_RING_OPACITY,
            ),
            hoverinfo="skip",
            showlegend=False,
        ))

    # ── 3. Node trace ──────────────────────────────────────────────────────────
    node_x, node_y, node_text, node_hover = [], [], [], []
    node_sizes, node_colors, node_line_widths, node_line_colors = [], [], [], []

    for fac_id, lay in layout.items():
        row = _facility_row(net_df, fac_id)
        status = fac_status.get(fac_id, "ok")
        color = STATUS_COLORS.get(status, STATUS_COLORS["ok"])
        size = NODE_SIZES.get(lay["type"], 12)

        node_x.append(lay["x"])
        node_y.append(lay["y"])
        node_text.append(fac_id)
        node_hover.append(_build_hover_text(fac_id, lay, row or {}))
        node_sizes.append(size)
        node_colors.append(color)

        # Highlight selected facility with white outline
        if fac_id == selected_facility:
            node_line_widths.append(3)
            node_line_colors.append("#ffffff")
        else:
            node_line_widths.append(1)
            node_line_colors.append("#1f2937")

    traces.append(go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=node_line_widths, color=node_line_colors),
        ),
        text=node_text,
        textposition="top center",
        textfont=dict(size=9, color="#1f2937"),
        hovertext=node_hover,
        hovertemplate="%{hovertext}<extra></extra>",
        showlegend=False,
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
        xaxis=dict(visible=False, range=[-0.05, 1.05]),
        yaxis=dict(visible=False, range=[-0.05, 1.05], scaleanchor="x"),
        title=dict(text=f"{network_id} · Tick {tick}", font=dict(size=12), x=0.5),
        showlegend=False,
    )
    return fig


def build_mini_map(
    tick_df: pd.DataFrame,
    tick: int,
    network_id: str,
    layout: dict[str, FacilityLayout],
) -> go.Figure:
    """Build a simplified ~200×200px mini-map for Tab 2 multi-hub overview.

    No tooltips, no text labels — colour-only status encoding.

    Args:
        tick_df: All FlatTickSnapshot rows for this tick.
        tick: Current tick index.
        network_id: Which network to render.
        layout: {facility_id: FacilityLayout}.

    Returns:
        go.Figure — empty figure if tick_df is empty.
    """
    if tick_df.empty or not layout:
        return go.Figure()

    net_df = tick_df[tick_df["network_id"] == network_id]
    if net_df.empty:
        return go.Figure()

    node_x, node_y, node_colors, node_sizes = [], [], [], []

    for fac_id, lay in layout.items():
        row = _facility_row(net_df, fac_id)
        status = row["status"] if row else "ok"
        color = STATUS_COLORS.get(status, STATUS_COLORS["ok"])
        # Mini-map uses smaller sizes
        size = max(4, NODE_SIZES.get(lay["type"], 8) // 2)

        node_x.append(lay["x"])
        node_y.append(lay["y"])
        node_colors.append(color)
        node_sizes.append(size)

    fig = go.Figure(data=[go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        marker=dict(size=node_sizes, color=node_colors),
        hoverinfo="skip",
        showlegend=False,
    )])
    fig.update_layout(
        width=200,
        height=200,
        margin=dict(l=4, r=4, t=18, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
        xaxis=dict(visible=False, range=[-0.05, 1.05]),
        yaxis=dict(visible=False, range=[-0.05, 1.05], scaleanchor="x"),
        title=dict(text=network_id, font=dict(size=9), x=0.5),
        showlegend=False,
    )
    return fig
