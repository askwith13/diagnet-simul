"""Tab 3 — Facility Detail renderer."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from core.models import AlertRecord

# Threshold pairs (warn, critical) per field — PRD §5.1
_THRESHOLDS: dict[str, tuple[float, float]] = {
    "patients_queued":     (35.0, 55.0),
    "cartridges":          (25.0, 10.0),
    "tat_hours":           (24.0, 36.0),
    "cascade_dropout_risk":(0.35, 0.60),
}

_FIELD_LABELS = {
    "patients_queued":     "Patients Queued",
    "cartridges":          "Cartridges",
    "tat_hours":           "TAT (hours)",
    "cascade_dropout_risk":"Cascade Dropout Risk",
}

_SHAP_LABELS = {
    "patients_queued":        "Queue load",
    "cartridges":             "Cartridges",
    "truenat_chips":          "Truenat chips",
    "tat_hours":              "TAT",
    "hr_on_shift":            "HR on shift",
    "machines":               "Machines",
    "modules":                "Modules",
    "daily_consumption":      "Daily consumption",
    "bayesian_stockout_prob": "Stockout risk",
    "cascade_dropout_risk":   "Cascade risk",
}


def get_most_recent_alert(
    alerts: list[AlertRecord],
    facility_id: str,
    up_to_tick: int,
) -> AlertRecord | None:
    """Return the most recently fired alert for facility_id up to up_to_tick."""
    candidates = [
        a for a in alerts
        if a.facility_id == facility_id and a.tick <= up_to_tick
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda a: a.tick)


def get_recommended_actions(
    payload: dict[str, Any],
    facility_id: str,
) -> list[str]:
    """Return up to 3 recommended action strings for the facility."""
    recommended = payload["metadata"].get("recommended_actions", {})
    actions = recommended.get(facility_id, [])
    return actions[:3]


def build_time_series_figure(
    tick_df: pd.DataFrame,
    field: str,
    facility_id: str,
    up_to_tick: int,
) -> go.Figure:
    """Build a Plotly line chart for one metric, with threshold lines.

    Shows all ticks from 0 to up_to_tick for the selected facility.
    Returns an empty figure if tick_df is empty or facility not found.
    """
    if tick_df.empty:
        return go.Figure()

    fac_df = tick_df[tick_df["facility_id"] == facility_id].sort_values("tick")
    fac_df = fac_df[fac_df["tick"] <= up_to_tick]

    if fac_df.empty or field not in fac_df.columns:
        return go.Figure()

    label = _FIELD_LABELS.get(field, field.replace("_", " ").title())
    warn, crit = _THRESHOLDS.get(field, (None, None))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=fac_df["tick"],
        y=fac_df[field],
        mode="lines+markers",
        marker=dict(size=4),
        line=dict(color="#3b82f6", width=2),
        name=label,
    ))

    if warn is not None:
        fig.add_hline(
            y=warn, line_dash="dot",
            line_color="#f59e0b", line_width=1,
            annotation_text="warn", annotation_position="right",
        )
    if crit is not None:
        fig.add_hline(
            y=crit, line_dash="dash",
            line_color="#ef4444", line_width=1,
            annotation_text="critical", annotation_position="right",
        )

    fig.update_layout(
        title=dict(text=label, font=dict(size=12), x=0.5),
        margin=dict(l=8, r=40, t=30, b=8),
        showlegend=False,
        height=180,
        xaxis=dict(title="Tick", tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
    )
    return fig


def build_shap_waterfall_figure(
    shap_contributions: dict[str, float],
    top_n: int = 5,
) -> go.Figure:
    """Build a horizontal bar chart of SHAP contributions.

    Labelled 'Approximate · simulation mode'.
    Returns empty figure if no contributions.
    """
    if not shap_contributions:
        return go.Figure()

    top = sorted(shap_contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]
    fields = [_SHAP_LABELS.get(f, f.replace("_", " ").title()) for f, _ in top]
    values = [v for _, v in top]
    colors = ["#3b82f6" if v >= 0 else "#ef4444" for v in values]

    fig = go.Figure(go.Bar(
        x=values,
        y=fields,
        orientation="h",
        marker_color=colors,
        text=[f"+{v:.3f}" if v >= 0 else f"{v:.3f}" for v in values],
        textposition="auto",
    ))
    fig.update_layout(
        title=dict(
            text="SHAP · Approximate · simulation mode",
            font=dict(size=11, color="#64748b"),
            x=0.5,
        ),
        margin=dict(l=8, r=8, t=30, b=8),
        showlegend=False,
        height=200,
        xaxis=dict(title="Contribution", tickfont=dict(size=9), zeroline=True),
        yaxis=dict(autorange="reversed", tickfont=dict(size=9)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,249,250,1)",
    )
    return fig


def render_facility_tab(
    scenario_data: dict[str, Any],
    current_scenario: str,
    tick: int,
    selected_facility: str | None,
) -> None:
    """Render Tab 3 — Facility Detail with time-series, SHAP waterfall, actions."""
    import streamlit as st

    if selected_facility is None:
        st.info("Click any node on the Network Map to open facility detail.")
        return

    payload = scenario_data.get(current_scenario, {})
    tick_df: pd.DataFrame = payload.get("tick_df", pd.DataFrame())
    alerts: list[AlertRecord] = payload.get("alerts", [])

    # Facility header
    fac_rows = tick_df[
        (tick_df["facility_id"] == selected_facility) & (tick_df["tick"] == tick)
    ]
    status = fac_rows["status"].iloc[0] if not fac_rows.empty else "ok"
    status_colour = {"ok": "green", "warning": "orange", "critical": "red", "offline": "grey"}
    sc = status_colour.get(status, "grey")
    st.markdown(
        f'### {selected_facility} '
        f'<span style="color:{sc};font-size:14px;">● {status.upper()}</span>',
        unsafe_allow_html=True,
    )

    # 4 time-series charts
    chart_cols = st.columns(2)
    chart_fields = ["patients_queued", "cartridges", "tat_hours", "cascade_dropout_risk"]
    for i, field in enumerate(chart_fields):
        with chart_cols[i % 2]:
            fig = build_time_series_figure(tick_df, field, selected_facility, tick)
            st.plotly_chart(fig, use_container_width=True, key=f"ts_{field}_{selected_facility}")

    # SHAP waterfall
    recent_alert = get_most_recent_alert(alerts, selected_facility, tick)
    if recent_alert and recent_alert.shap_contributions:
        st.markdown("**SHAP Feature Contributions**")
        fig = build_shap_waterfall_figure(recent_alert.shap_contributions)
        st.plotly_chart(fig, use_container_width=True, key=f"shap_{selected_facility}_{tick}")
    else:
        st.caption("No alerts fired for this facility yet — SHAP waterfall will appear once an alert fires.")

    # Recommended actions
    actions = get_recommended_actions(payload, selected_facility)
    if actions:
        st.markdown("**Recommended Actions**")
        for action in actions:
            st.markdown(f"- {action}")

    # Alert history
    fac_alerts = [a for a in alerts if a.facility_id == selected_facility and a.tick <= tick]
    if fac_alerts:
        st.markdown("**Alert History**")
        for a in sorted(fac_alerts, key=lambda x: x.tick, reverse=True):
            st.caption(f"Tick {a.tick} · {a.alert_type.upper()} · {a.message}")
