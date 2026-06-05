"""DiagNet Simulation Platform — Streamlit entry point.

Wiring only: startup validation, data load, session init, tab routing.
No business logic lives here — all computation is in loader.py, viz/,
tabs/, session.py, and playback.py.
"""
from __future__ import annotations

import time

import streamlit as st
import yaml
from pathlib import Path

from core.network_layout import load_all_layouts, load_network_links
from loader import load_scenario_payloads, load_metadata, validate_data_exists
from playback import apply_playback_step, get_interval_s, is_at_end
from session import (
    CURRENT_SCENARIO,
    GRAPH_CACHE,
    IS_PLAYING,
    PERF_LOG,
    SCENARIO_DATA,
    SCENARIO_SNAPSHOTS,
    SELECTED_FACILITY,
    TICK_CURSOR,
    init_session_state,
)
from tabs.export import render_export_tab
from tabs.facility import render_facility_tab
from tabs.network import render_network_tab
from tabs.overview import render_overview_tab

# ─── Page config (must be first Streamlit call) ───────────────────────────────

st.set_page_config(
    page_title="DiagNet — Diagnostic Network Intelligence",
    page_icon="🔬",
    layout="wide",
)

# ─── Startup: validate + load (runs once per session) ─────────────────────────

if SCENARIO_DATA not in st.session_state:
    t_start = time.perf_counter()

    # 1. Load and validate metadata
    try:
        metadata = load_metadata()
    except FileNotFoundError:
        st.error(
            "Pre-computed data missing. Run: "
            "`uv run python scripts/generate_scenarios.py --all`"
        )
        st.stop()

    missing = validate_data_exists(metadata)
    if missing:
        st.error(
            "Pre-computed data missing. Run: "
            "`uv run python scripts/generate_scenarios.py --all`\n\n"
            f"Missing files: {', '.join(missing[:3])}"
            + (" (and more)" if len(missing) > 3 else "")
        )
        st.stop()

    # 2. Load all 8 scenarios eagerly
    scenario_data = load_scenario_payloads()

    # 3. Load network layouts + links into graph cache
    networks_data = yaml.safe_load(Path("config/networks.yaml").read_text())
    graph_cache = {
        net_id: {
            "layout": load_all_layouts(networks_data)[net_id],
            "links":  load_network_links(networks_data, net_id),
        }
        for net_id in networks_data["networks"]
    }

    # 4. Initialise session state
    init_session_state(scenario_data, st.session_state)
    st.session_state[GRAPH_CACHE] = graph_cache

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    st.session_state[PERF_LOG].append(elapsed_ms)

# ─── Persistent top bar ───────────────────────────────────────────────────────

scenario_data: dict = st.session_state[SCENARIO_DATA]
scenario_ids = sorted(scenario_data.keys())
scenario_labels = {
    sc_id: scenario_data[sc_id]["metadata"]["display_name"]
    for sc_id in scenario_ids
}

col_net, col_sc, col_play, col_speed, col_tick, col_badge = st.columns(
    [1.5, 2.5, 1.5, 1.5, 1.5, 1]
)

with col_net:
    all_net_options = ["All networks"] + ["NET-A", "NET-B", "NET-C", "NET-D", "NET-E"]
    # If scenario just changed, reset network to "All networks" before creating the widget
    if st.session_state.pop("_reset_network", False):
        st.session_state["_network_selector"] = "All networks"
    selected_network = st.selectbox(
        "Network", all_net_options, label_visibility="collapsed",
        key="_network_selector",
    )

with col_sc:
    current_sc = st.session_state[CURRENT_SCENARIO]
    sc_index = scenario_ids.index(current_sc) if current_sc in scenario_ids else 0
    chosen_sc = st.selectbox(
        "Scenario",
        scenario_ids,
        index=sc_index,
        format_func=lambda x: f"{x.upper()} · {scenario_labels[x]}",
        label_visibility="collapsed",
        key="_scenario_selector",
    )
    if chosen_sc != st.session_state[CURRENT_SCENARIO]:
        st.session_state[CURRENT_SCENARIO] = chosen_sc
        st.session_state[TICK_CURSOR] = 0
        st.session_state[IS_PLAYING] = False
        st.session_state[SELECTED_FACILITY] = None
        # Flag that the network selector should reset on next render.
        # We cannot set _network_selector here (widget already rendered),
        # so use a separate flag checked before the widget renders.
        st.session_state["_reset_network"] = True
        st.rerun()

with col_play:
    max_ticks = scenario_data[st.session_state[CURRENT_SCENARIO]]["metadata"]["tick_count"]
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("▶", help="Play", use_container_width=True):
            if not is_at_end(st.session_state[TICK_CURSOR], max_ticks):
                st.session_state[IS_PLAYING] = True
    with c2:
        if st.button("⏸", help="Pause", use_container_width=True):
            st.session_state[IS_PLAYING] = False
    with c3:
        if st.button("⏮", help="Rewind", use_container_width=True):
            st.session_state[TICK_CURSOR] = 0
            st.session_state[IS_PLAYING] = False
            st.session_state[SELECTED_FACILITY] = None

with col_speed:
    speed = st.slider(
        "Playback Speed", min_value=0.5, max_value=4.0,
        value=1.0, step=0.5, label_visibility="collapsed",
        key="_speed_slider",
    )

with col_tick:
    tick = st.session_state[TICK_CURSOR]
    st.progress(tick / max(max_ticks - 1, 1), text=f"Tick {tick} / {max_ticks - 1}")

with col_badge:
    # Global alert count badge (updated once tab content is rendered)
    active_sc = st.session_state[CURRENT_SCENARIO]
    n_alerts = len(scenario_data[active_sc]["alerts"])
    badge_colour = "red" if n_alerts > 0 else "green"
    st.markdown(
        f'<div style="text-align:center;font-size:11px;color:{badge_colour};">'
        f'🔔 {n_alerts}</div>',
        unsafe_allow_html=True,
    )

# ─── Tabs ─────────────────────────────────────────────────────────────────────

# Resolve effective network for Tab 1: use scenario's primary_network when
# "All networks" is selected (Tab 1 always shows one network at a time).
primary_net = (
    scenario_data[st.session_state[CURRENT_SCENARIO]]["metadata"]
    .get("primary_network", "NET-A")
)
effective_network = primary_net if selected_network == "All networks" else selected_network

tab1, tab2, tab3, tab4 = st.tabs([
    "🗺 Network Map",
    "🌐 Multi-Hub Overview",
    "🏥 Facility Detail",
    "📊 Analytics & Export",
])

with tab1:
    render_network_tab(
        scenario_data=scenario_data,
        current_scenario=st.session_state[CURRENT_SCENARIO],
        tick=st.session_state[TICK_CURSOR],
        selected_facility=st.session_state[SELECTED_FACILITY],
        graph_cache=st.session_state[GRAPH_CACHE],
        network_id=effective_network,
    )

with tab2:
    render_overview_tab(
        scenario_data=scenario_data,
        current_scenario=st.session_state[CURRENT_SCENARIO],
        tick=st.session_state[TICK_CURSOR],
        graph_cache=st.session_state[GRAPH_CACHE],
    )

with tab3:
    render_facility_tab(
        scenario_data=scenario_data,
        current_scenario=st.session_state[CURRENT_SCENARIO],
        tick=st.session_state[TICK_CURSOR],
        selected_facility=st.session_state[SELECTED_FACILITY],
    )

with tab4:
    render_export_tab(
        scenario_data=scenario_data,
        scenario_snapshots=st.session_state[SCENARIO_SNAPSHOTS],
    )

# ─── Playback loop ────────────────────────────────────────────────────────────

if st.session_state[IS_PLAYING]:
    t0 = time.perf_counter()
    time.sleep(get_interval_s(speed))
    active_sc = st.session_state[CURRENT_SCENARIO]
    did_advance = apply_playback_step(
        state=st.session_state,
        max_ticks=max_ticks,
        current_scenario=active_sc,
        scenario_tick_df=scenario_data[active_sc]["tick_df"],
    )
    render_ms = (time.perf_counter() - t0) * 1000
    st.session_state[PERF_LOG].append(render_ms)
    if did_advance:
        st.rerun()
