"""Tab 1 — Network Map renderer."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from core.models import AlertRecord
from viz.alerts import build_alert_cards
from viz.network_map import build_network_figure

# Thresholds for metrics bar (PRD §5.1)
_CARTRIDGE_WARN = 25.0
_CHIPS_WARN = 15.0
_STATUS_CRITICAL = "critical"
_STATUS_WARNING = "warning"


def compute_metrics(tick_df: pd.DataFrame, network_id: str) -> dict[str, float]:
    """Compute the 5 metrics bar values for a given network at the current tick.

    Returns dict with keys: critical_count, warning_count, total_queued,
    low_cartridge_count, avg_dropout_risk.
    """
    net = tick_df[tick_df["network_id"] == network_id] if not tick_df.empty else tick_df

    if net.empty:
        return {
            "critical_count": 0,
            "warning_count": 0,
            "total_queued": 0.0,
            "low_cartridge_count": 0,
            "avg_dropout_risk": 0.0,
        }

    # Only count facilities that HAVE the consumable (non-zero means they use it)
    low_consumable = int(
        ((net["cartridges"] > 0) & (net["cartridges"] < _CARTRIDGE_WARN)).sum()
        + ((net["truenat_chips"] > 0) & (net["truenat_chips"] < _CHIPS_WARN)).sum()
    )
    return {
        "critical_count":      int((net["status"] == _STATUS_CRITICAL).sum()),
        "warning_count":       int((net["status"] == _STATUS_WARNING).sum()),
        "total_queued":        float(net["patients_queued"].sum()),
        "low_cartridge_count": low_consumable,
        "avg_dropout_risk":    float(net["cascade_dropout_risk"].mean()),
    }


def get_active_reroutes(payload: dict[str, Any], tick: int) -> list[list[str]] | None:
    """Return reroute pairs if the scenario recommendation alert has fired.

    Reroutes become active once tick >= the tick of the first recommendation alert.
    Returns None if no recommendation alert has fired yet.
    """
    reroutes: list[list] = payload["metadata"].get("reroutes", [])
    if not reroutes:
        return None

    alerts: list[AlertRecord] = payload["alerts"]
    first_recommendation_tick = next(
        (a.tick for a in alerts if a.alert_type in ("recommendation", "reroute")),
        None,
    )
    if first_recommendation_tick is None or tick < first_recommendation_tick:
        return None

    return [[str(r[0]), str(r[1])] for r in reroutes if len(r) >= 2]


def render_network_tab(
    scenario_data: dict[str, Any],
    current_scenario: str,
    tick: int,
    selected_facility: str | None,
    graph_cache: dict[str, Any],
    network_id: str = "NET-A",
) -> None:
    """Render Tab 1 — Network Map, alert panel, metrics bar."""
    import streamlit as st
    from session import SELECTED_FACILITY

    payload = scenario_data.get(current_scenario, {})
    tick_df: pd.DataFrame = payload.get("tick_df", pd.DataFrame())
    alerts: list[AlertRecord] = payload.get("alerts", [])

    # Filter tick_df to current tick
    cur_tick_df = tick_df[tick_df["tick"] == tick] if not tick_df.empty else tick_df

    # Alerts fired up to and including current tick
    alerts_so_far = [a for a in alerts if a.tick <= tick]

    net_cache = graph_cache.get(network_id, {})
    layout = net_cache.get("layout", {})
    links = net_cache.get("links", [])
    active_reroutes = get_active_reroutes(payload, tick)

    # ── Layout: map (left 3/4) + alert panel (right 1/4) ──────────────────────
    col_map, col_alerts = st.columns([3, 1])

    with col_map:
        fig = build_network_figure(
            tick_df=cur_tick_df,
            tick=tick,
            network_id=network_id,
            layout=layout,
            links=links,
            selected_facility=selected_facility,
            active_reroutes=active_reroutes,
        )
        clicked = st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"net_map_{current_scenario}_{tick}",
            on_select="rerun",
            selection_mode="points",
        )
        # Handle node click → set selected facility
        if clicked and hasattr(clicked, "selection") and clicked.selection:
            pts = clicked.selection.get("points", [])
            if pts and "text" in pts[0]:
                st.session_state[SELECTED_FACILITY] = pts[0]["text"]
                st.rerun()

    with col_alerts:
        # Filter alerts to selected network
        net_alerts = [a for a in alerts_so_far if a.network_id == network_id]
        st.markdown(
            build_alert_cards(net_alerts, max_cards=14),
            unsafe_allow_html=True,
        )

    # ── Metrics bar ────────────────────────────────────────────────────────────
    m = compute_metrics(cur_tick_df, network_id)
    prev_tick_df = tick_df[tick_df["tick"] == max(0, tick - 1)] if not tick_df.empty else cur_tick_df
    prev_m = compute_metrics(prev_tick_df, network_id)

    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1:
        st.metric("🔴 Critical sites", m["critical_count"],
                  delta=m["critical_count"] - prev_m["critical_count"])
    with mc2:
        st.metric("🟡 At-risk sites", m["warning_count"],
                  delta=m["warning_count"] - prev_m["warning_count"])
    with mc3:
        st.metric("👥 Total queued", f"{m['total_queued']:.0f}",
                  delta=f"{m['total_queued'] - prev_m['total_queued']:.0f}")
    with mc4:
        st.metric("💊 Low consumable", m["low_cartridge_count"],
                  delta=m["low_cartridge_count"] - prev_m["low_cartridge_count"])
    with mc5:
        st.metric("⚠️ Avg dropout risk", f"{m['avg_dropout_risk']:.1%}",
                  delta=f"{m['avg_dropout_risk'] - prev_m['avg_dropout_risk']:.1%}")
