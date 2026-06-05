"""Tab 2 — Multi-Hub Overview renderer."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from core.models import AlertRecord
from viz.alerts import build_alert_cards
from viz.network_map import build_mini_map

# Positions for the 5 networks in the inter-network diagram (x, y on 0-1 canvas)
_NET_POSITIONS: dict[str, tuple[float, float]] = {
    "NET-A": (0.50, 0.20),  # Chandrapur — central
    "NET-B": (0.15, 0.50),  # Balaghat — west
    "NET-C": (0.85, 0.20),  # Yavatmal — east
    "NET-D": (0.50, 0.80),  # Gadchiroli — south
    "NET-E": (0.20, 0.80),  # Amravati — south-west
}
_NET_LABELS: dict[str, str] = {
    "NET-A": "Chandrapur",
    "NET-B": "Balaghat",
    "NET-C": "Yavatmal",
    "NET-D": "Gadchiroli",
    "NET-E": "Amravati",
}
# Static inter-network links from PRD §4.3
_INTER_LINKS = [
    ("NET-A", "NET-C", "culture_dst"),
    ("NET-B", "NET-D", "overflow"),
    ("NET-D", "NET-A", "overflow"),
]


def build_bottleneck_heatmap(tick_df: pd.DataFrame) -> go.Figure:
    """Build a horizontal bar chart of patients_queued for all 59 nodes.

    Sorted descending; colour-coded by facility status.
    patients_queued changes every tick — makes the chart dynamically useful.

    Returns empty figure if tick_df is empty.
    """
    if tick_df.empty or "patients_queued" not in tick_df.columns:
        return go.Figure()

    df = tick_df[["facility_id", "patients_queued", "status", "network_id"]].copy()
    df = df[df["patients_queued"] > 0]   # skip zero-queue facilities for clarity
    df = df.sort_values("patients_queued", ascending=True)  # ascending for horizontal bar

    _STATUS_COLOUR = {
        "ok":       "#22c55e",
        "warning":  "#f59e0b",
        "critical": "#ef4444",
        "offline":  "#808080",
    }
    colors = [_STATUS_COLOUR.get(str(s), "#22c55e") for s in df["status"]]

    fig = go.Figure(go.Bar(
        x=df["patients_queued"],
        y=df["facility_id"],
        orientation="h",
        marker_color=colors,
        hovertemplate="%{y}: %{x:.0f} patients queued<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="System-wide Patient Queue (all facilities with active queue)", font=dict(size=12), x=0.5),
        margin=dict(l=10, r=10, t=35, b=10),
        height=500,
        xaxis=dict(title="Patients queued", tickfont=dict(size=8)),
        yaxis=dict(tickfont=dict(size=7)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
        showlegend=False,
    )
    return fig


def build_inter_network_figure(
    network_critical: dict[str, bool],
) -> go.Figure:
    """Build a small diagram of the 5 networks with inter-network flow links.

    Args:
        network_critical: {network_id: bool} — True if network has a critical facility.

    Returns:
        go.Figure showing 5 network nodes + 3 inter-network links.
    """
    traces: list[go.BaseTraceType] = []

    # Edge traces
    for src, dst, flow_type in _INTER_LINKS:
        sx, sy = _NET_POSITIONS[src]
        dx, dy = _NET_POSITIONS[dst]
        is_stressed = network_critical.get(src, False) or network_critical.get(dst, False)
        colour = "#ef4444" if is_stressed else "#22c55e"
        dash = "dash" if flow_type == "overflow" else "dot"
        traces.append(go.Scatter(
            x=[sx, dx, None], y=[sy, dy, None],
            mode="lines",
            line=dict(color=colour, width=2, dash=dash),
            hoverinfo="skip",
            showlegend=False,
        ))

    # Node traces
    node_x = [_NET_POSITIONS[n][0] for n in _NET_POSITIONS]
    node_y = [_NET_POSITIONS[n][1] for n in _NET_POSITIONS]
    node_labels = [f"{n}<br><sub>{_NET_LABELS[n]}</sub>" for n in _NET_POSITIONS]
    node_colors = [
        "#ef4444" if network_critical.get(n, False) else "#22c55e"
        for n in _NET_POSITIONS
    ]
    traces.append(go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker=dict(size=30, color=node_colors, line=dict(width=1, color="#1f2937")),
        text=list(_NET_POSITIONS.keys()),
        textposition="middle center",
        textfont=dict(size=8, color="#ffffff"),
        hovertext=node_labels,
        hovertemplate="%{hovertext}<extra></extra>",
        showlegend=False,
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        margin=dict(l=5, r=5, t=25, b=5),
        height=220,
        title=dict(text="Inter-network flows", font=dict(size=11), x=0.5),
        xaxis=dict(visible=False, range=[-0.1, 1.1]),
        yaxis=dict(visible=False, range=[-0.1, 1.1]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
        showlegend=False,
    )
    return fig


def get_global_alerts(
    alerts: list[AlertRecord],
    up_to_tick: int,
) -> list[AlertRecord]:
    """Return all alerts across all networks up to up_to_tick, sorted most-recent-first."""
    return sorted(
        (a for a in alerts if a.tick <= up_to_tick),
        key=lambda a: a.tick,
        reverse=True,
    )


def compute_network_critical(tick_df: pd.DataFrame) -> dict[str, bool]:
    """Return {network_id: True} if any facility in that network is critical."""
    if tick_df.empty:
        return {}
    result = {}
    for net_id in tick_df["network_id"].unique():
        net = tick_df[tick_df["network_id"] == net_id]
        result[str(net_id)] = bool((net["status"] == "critical").any())
    return result


def render_overview_tab(
    scenario_data: dict[str, Any],
    current_scenario: str,
    tick: int,
    graph_cache: dict[str, Any],
) -> None:
    """Render Tab 2 — Multi-Hub Overview."""
    import streamlit as st
    from session import CURRENT_SCENARIO, IS_PLAYING, TICK_CURSOR

    payload = scenario_data.get(current_scenario, {})
    tick_df: pd.DataFrame = payload.get("tick_df", pd.DataFrame())
    alerts: list[AlertRecord] = payload.get("alerts", [])

    cur_tick_df = tick_df[tick_df["tick"] == tick] if not tick_df.empty else tick_df
    network_critical = compute_network_critical(cur_tick_df)

    # ── Run SC-08 button ──────────────────────────────────────────────────────
    sc08_col, _ = st.columns([1, 4])
    with sc08_col:
        if st.button("▶ Run SC-08 — Full Recovery", use_container_width=True,
                     help="Launch SC-08: Full network recovery across all 5 networks"):
            st.session_state[CURRENT_SCENARIO] = "sc-08"
            st.session_state[TICK_CURSOR] = 0
            st.session_state[IS_PLAYING] = True
            st.rerun()

    st.divider()

    # ── 5-column mini-map grid ────────────────────────────────────────────────
    net_ids = ["NET-A", "NET-B", "NET-C", "NET-D", "NET-E"]
    cols = st.columns(5)
    for i, net_id in enumerate(net_ids):
        with cols[i]:
            net_cache = graph_cache.get(net_id, {})
            layout = net_cache.get("layout", {})
            fig = build_mini_map(cur_tick_df, tick, net_id, layout)
            st.plotly_chart(fig, width="stretch", key=f"mini_{net_id}_{tick}")

    # ── Inter-network flow diagram + bottleneck heatmap ───────────────────────
    col_flow, col_heat = st.columns([1, 2])

    with col_flow:
        fig_flow = build_inter_network_figure(network_critical)
        st.plotly_chart(fig_flow, width="stretch", key=f"inter_flow_{tick}")

    with col_heat:
        fig_heat = build_bottleneck_heatmap(cur_tick_df)
        st.plotly_chart(fig_heat, width="stretch", key=f"heatmap_{tick}")

    # ── Global alert feed ─────────────────────────────────────────────────────
    st.markdown("**Global Alert Feed**")
    global_alerts = get_global_alerts(alerts, tick)
    if global_alerts:
        # Annotate messages with network badge
        for a in global_alerts[:14]:
            badge = f"[{a.network_id}]"
            if badge not in a.message:
                a = AlertRecord(
                    tick=a.tick,
                    facility_id=a.facility_id,
                    network_id=a.network_id,
                    alert_type=a.alert_type,
                    message=f"{badge} {a.message}",
                    shap_contributions=a.shap_contributions,
                    severity=a.severity,
                )
        st.markdown(
            build_alert_cards(global_alerts, max_cards=14),
            unsafe_allow_html=True,
        )
    else:
        st.caption("No alerts yet — play a scenario to see global alerts.")
