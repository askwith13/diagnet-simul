"""Tab 4 — Analytics & Export renderer."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go

NETWORKS_YAML_PATH = Path("config/networks.yaml")

# Aggregation method per metric field
_METRIC_AGG: dict[str, str] = {
    "patients_queued":        "sum",
    "cartridges":             "sum",
    "truenat_chips":          "sum",
    "tat_hours":              "mean",
    "hr_on_shift":            "mean",
    "cascade_dropout_risk":   "mean",
    "bayesian_stockout_prob": "mean",
    "bottleneck_score":       "mean",
    "effective_capacity_days":"mean",
}

# Human-readable metric labels for the dropdown
COMPARISON_METRICS: dict[str, str] = {
    "patients_queued":        "Total patients queued",
    "cartridges":             "Total cartridges",
    "truenat_chips":          "Total Truenat chips",
    "tat_hours":              "Mean TAT (hours)",
    "cascade_dropout_risk":   "Mean cascade dropout risk",
    "bayesian_stockout_prob": "Mean P(stockout 14d)",
    "bottleneck_score":       "Mean bottleneck score",
}

_LINE_COLOURS = ["#3b82f6", "#ef4444"]


# ─── Pure helpers ─────────────────────────────────────────────────────────────

def is_screenshot_enabled() -> bool:
    """Return True unless DIAGNET_SCREENSHOT_ENABLED is explicitly set to 'false'."""
    return os.environ.get("DIAGNET_SCREENSHOT_ENABLED", "true").lower() != "false"


def build_comparison_figure(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    metric: str,
    label_a: str,
    label_b: str,
) -> go.Figure:
    """Build a dual-line Plotly chart comparing one metric across two scenarios.

    Aggregates the metric across all facilities per tick using the appropriate
    aggregation (sum for stock/count fields, mean for rate fields).

    Args:
        df_a: Full tick_df for scenario A.
        df_b: Full tick_df for scenario B.
        metric: Field name to compare (must be in FlatTickSnapshot).
        label_a: Display name for scenario A (line label).
        label_b: Display name for scenario B.

    Returns:
        go.Figure with two lines; empty figure if either df is empty or
        metric column is absent.
    """
    if df_a.empty or df_b.empty:
        return go.Figure()
    if metric not in df_a.columns or metric not in df_b.columns:
        return go.Figure()

    agg_func = _METRIC_AGG.get(metric, "mean")

    series_a = df_a.groupby("tick")[metric].agg(agg_func).reset_index()
    series_b = df_b.groupby("tick")[metric].agg(agg_func).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series_a["tick"], y=series_a[metric],
        mode="lines+markers",
        name=label_a,
        line=dict(color=_LINE_COLOURS[0], width=2),
        marker=dict(size=4),
    ))
    fig.add_trace(go.Scatter(
        x=series_b["tick"], y=series_b[metric],
        mode="lines+markers",
        name=label_b,
        line=dict(color=_LINE_COLOURS[1], width=2),
        marker=dict(size=4),
    ))

    readable_metric = COMPARISON_METRICS.get(metric, metric.replace("_", " ").title())
    fig.update_layout(
        title=dict(text=f"{readable_metric} — Scenario Comparison", font=dict(size=13), x=0.5),
        xaxis=dict(title="Tick"),
        yaxis=dict(title=readable_metric),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
    )
    return fig


def take_screenshot(fig: go.Figure, output_path: str = "diagnet_screenshot.png") -> str:
    """Export a Plotly figure to a 1920×1080 PNG using kaleido.

    Args:
        fig: The Plotly figure to export.
        output_path: Local file path for the PNG.

    Returns:
        The resolved absolute path string of the saved file.

    Raises:
        ImportError: If kaleido is not installed.
        ValueError: If fig is empty (no data).
    """
    import plotly.io as pio
    if not fig.data:
        raise ValueError("Cannot screenshot an empty figure.")
    pio.write_image(fig, output_path, engine="kaleido", width=1920, height=1080)
    return str(Path(output_path).resolve())


# ─── Streamlit renderer ───────────────────────────────────────────────────────

def render_export_tab(
    scenario_data: dict[str, Any],
    scenario_snapshots: dict[str, Any],
) -> None:
    """Render Tab 4 — Scenario Comparison, Config Viewer, Screenshot."""
    import streamlit as st

    st.subheader("Scenario Comparison")

    snapshot_ids = list(scenario_snapshots.keys())
    if len(snapshot_ids) < 2:
        st.info(
            "Run two scenarios to completion (press Play and let them finish) "
            "to enable comparison. "
            f"Completed so far: {snapshot_ids or 'none'}."
        )
    else:
        col_a, col_b, col_m = st.columns(3)
        with col_a:
            sc_a = st.selectbox(
                "Scenario A", snapshot_ids, index=0,
                format_func=lambda x: scenario_data[x]["metadata"]["display_name"] if x in scenario_data else x,
                key="_compare_a",
            )
        with col_b:
            sc_b = st.selectbox(
                "Scenario B", snapshot_ids, index=min(1, len(snapshot_ids) - 1),
                format_func=lambda x: scenario_data[x]["metadata"]["display_name"] if x in scenario_data else x,
                key="_compare_b",
            )
        with col_m:
            metric = st.selectbox(
                "Metric",
                list(COMPARISON_METRICS.keys()),
                format_func=lambda x: COMPARISON_METRICS[x],
                key="_compare_metric",
            )

        df_a = scenario_snapshots.get(sc_a, pd.DataFrame())
        df_b = scenario_snapshots.get(sc_b, pd.DataFrame())
        label_a = scenario_data.get(sc_a, {}).get("metadata", {}).get("display_name", sc_a)
        label_b = scenario_data.get(sc_b, {}).get("metadata", {}).get("display_name", sc_b)

        fig = build_comparison_figure(df_a, df_b, metric, label_a, label_b)
        if fig.data:
            st.plotly_chart(fig, use_container_width=True, key=f"compare_{sc_a}_{sc_b}_{metric}")
        else:
            st.warning("Could not build comparison chart — check that both scenarios completed.")

    st.divider()

    # ── Config Viewer ─────────────────────────────────────────────────────────
    st.subheader("Configuration Viewer")
    if NETWORKS_YAML_PATH.exists():
        yaml_text = NETWORKS_YAML_PATH.read_text()
        with st.expander("networks.yaml (read-only)", expanded=False):
            st.code(yaml_text, language="yaml")
        st.download_button(
            label="⬇ Download networks.yaml",
            data=yaml_text.encode(),
            file_name="networks.yaml",
            mime="text/yaml",
            key="_download_config",
        )
    else:
        st.warning(f"Config file not found: {NETWORKS_YAML_PATH}")

    st.divider()

    # ── Screenshot ────────────────────────────────────────────────────────────
    st.subheader("Screenshot Export")
    st.caption("Exports the active Tab 1 network map figure as a 1920×1080 PNG.")

    if not is_screenshot_enabled():
        st.info("Screenshot disabled in this environment.")
    else:
        if st.button("📸 Save Screenshot (PNG)", key="_screenshot_btn"):
            # Build a fresh figure from the current scenario/tick for export
            try:
                from core.network_layout import load_network_layout, load_network_links
                from session import CURRENT_SCENARIO, SCENARIO_DATA, TICK_CURSOR
                import yaml as _yaml

                # Use session state if available, else fall back to first scenario tick 0
                current_sc = st.session_state.get(CURRENT_SCENARIO, list(scenario_data.keys())[0])
                current_tick = st.session_state.get(TICK_CURSOR, 0)
                payload = scenario_data.get(current_sc, {})
                tick_df = payload.get("tick_df", pd.DataFrame())
                cur_tick_df = tick_df[tick_df["tick"] == current_tick] if not tick_df.empty else tick_df

                networks_data = _yaml.safe_load(NETWORKS_YAML_PATH.read_text())
                layout = load_network_layout(networks_data, "NET-A")
                links = load_network_links(networks_data, "NET-A")

                from viz.network_map import build_network_figure
                fig = build_network_figure(cur_tick_df, current_tick, "NET-A", layout, links)

                path = take_screenshot(fig)
                st.success(f"Screenshot saved: diagnet_screenshot.png")
            except Exception as exc:
                st.error(f"Screenshot failed: {exc}")
