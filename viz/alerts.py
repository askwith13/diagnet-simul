"""Stateless alert card and SHAP bar renderers.

Pure functions: (data) → HTML string.
No session_state reads or writes. No generation/ imports.
All HTML uses inline styles for Streamlit compatibility.
"""
from __future__ import annotations

from core.models import AlertRecord

# ─── Constants ───────────────────────────────────────────────────────────────

# WCAG AA-compliant colour pairs (PRD §9)
_CARD_STYLES: dict[str, dict[str, str]] = {
    "critical":    {"bg": "#dc2626", "text": "#ffffff", "badge_bg": "#991b1b"},
    "dto_advisory":{"bg": "#fef3c7", "text": "#92400e", "badge_bg": "#fcd34d"},
    "bayesian":    {"bg": "#eff6ff", "text": "#1e40af", "badge_bg": "#bfdbfe"},
    "recommendation": {"bg": "#eff6ff", "text": "#1e40af", "badge_bg": "#bfdbfe"},
    "warning":     {"bg": "#fef3c7", "text": "#92400e", "badge_bg": "#fcd34d"},
    "info":        {"bg": "#f8fafc", "text": "#475569", "badge_bg": "#e2e8f0"},
}
_DEFAULT_STYLE = _CARD_STYLES["info"]

# Human-readable labels for SHAP field names
_FIELD_LABELS: dict[str, str] = {
    "patients_queued":        "Queue load",
    "cartridges":             "Cartridges",
    "truenat_chips":          "Truenat chips",
    "tat_hours":              "TAT",
    "hr_on_shift":            "HR on shift",
    "machines":               "Machines",
    "modules":                "Modules",
    "samples_per_module_per_day": "Samples/module",
    "daily_consumption":      "Daily consumption",
    "smear_positivity_rate":  "Smear positivity",
    "specimen_rejection_rate":"Specimen rejection",
    "referral_completion_rate":"Referral completion",
    "chw_available":          "CHW available",
    "bayesian_stockout_prob": "Stockout risk",
    "cascade_dropout_risk":   "Cascade risk",
    "travel_time_min":        "Travel time",
}

_PLACEHOLDER = "No alerts — simulation not started."


# ─── format_shap_bar ─────────────────────────────────────────────────────────

def format_shap_bar(
    shap_contributions: dict[str, float],
    top_n: int = 2,
) -> str:
    """Format top-N SHAP contributions as a compact readable string.

    Args:
        shap_contributions: {field_name: shap_value} dict.
        top_n: Number of top contributors to show (by |value|).

    Returns:
        E.g. "↑ Queue load (+3.24) · ↑ TAT (+0.84)"
        Returns "" if contributions is empty.
    """
    if not shap_contributions:
        return ""

    top = sorted(shap_contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]

    parts: list[str] = []
    for field, val in top:
        label = _FIELD_LABELS.get(field, field.replace("_", " ").title())
        arrow = "↑" if val >= 0 else "↓"
        sign = "+" if val >= 0 else ""
        parts.append(f"{arrow} {label} ({sign}{val:.2f})")

    return " · ".join(parts)


# ─── build_alert_cards ────────────────────────────────────────────────────────

def build_alert_cards(
    alerts: list[AlertRecord],
    max_cards: int = 14,
) -> str:
    """Render alert records as an HTML string of styled cards.

    Args:
        alerts: List of AlertRecord objects.
        max_cards: Maximum number of cards to render (most-recent-first).

    Returns:
        HTML string ready for st.markdown(..., unsafe_allow_html=True).
        Returns placeholder text when alerts is empty.
    """
    if not alerts:
        return (
            f'<div style="color:#94a3b8;font-size:13px;padding:12px;'
            f'text-align:center;">{_PLACEHOLDER}</div>'
        )

    # Deduplicate same-tick, same-type, same-facility alerts
    seen: set[tuple] = set()
    deduped: list[AlertRecord] = []
    for a in alerts:
        key = (a.tick, a.alert_type, a.facility_id)
        if key not in seen:
            seen.add(key)
            deduped.append(a)

    # Most-recent-first, then truncate
    ordered = sorted(deduped, key=lambda a: a.tick, reverse=True)[:max_cards]

    cards: list[str] = []
    for alert in ordered:
        style = _CARD_STYLES.get(alert.alert_type.lower(), _DEFAULT_STYLE)
        badge_label = alert.alert_type.upper().replace("_", " ")
        shap_text = format_shap_bar(alert.shap_contributions, top_n=2)

        shap_html = ""
        if shap_text:
            shap_html = (
                f'<div style="font-size:11px;margin-top:4px;'
                f'opacity:0.85;font-style:italic;">'
                f'SHAP: {shap_text}</div>'
            )

        card_html = f"""<div style="
            background:{style['bg']};
            color:{style['text']};
            border-radius:6px;
            padding:8px 10px;
            margin-bottom:6px;
            font-size:13px;
            line-height:1.4;
        ">
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
    <span style="
        background:{style['badge_bg']};
        color:{style['text']};
        font-size:10px;
        font-weight:600;
        padding:2px 6px;
        border-radius:3px;
        text-transform:uppercase;
        letter-spacing:0.05em;
    ">{badge_label}</span>
    <span style="font-size:11px;opacity:0.75;">Tick {alert.tick}</span>
  </div>
  <div>{alert.message}</div>
  {shap_html}
</div>"""
        cards.append(card_html)

    return "\n".join(cards)
