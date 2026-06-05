"""Tests for viz/alerts.py — alert card and SHAP bar renderers."""
import pytest

from core.models import AlertRecord
from viz.alerts import _PLACEHOLDER, build_alert_cards, format_shap_bar


# ─── format_shap_bar ─────────────────────────────────────────────────────────

def test_format_shap_bar_worked_example():
    result = format_shap_bar({"patients_queued": 3.24, "tat_hours": 0.84})
    assert result == "↑ Queue load (+3.24) · ↑ TAT (+0.84)"


def test_format_shap_bar_negative_contribution():
    result = format_shap_bar({"cartridges": -1.40})
    assert result == "↓ Cartridges (-1.40)"


def test_format_shap_bar_top_2_only():
    result = format_shap_bar(
        {"patients_queued": 3.24, "tat_hours": 0.84, "cascade_dropout_risk": 0.032},
        top_n=2,
    )
    # Only top 2 by |value|
    assert "Queue load" in result
    assert "TAT" in result
    assert "Cascade risk" not in result


def test_format_shap_bar_top_1():
    result = format_shap_bar({"patients_queued": 3.24, "tat_hours": 0.84}, top_n=1)
    assert result == "↑ Queue load (+3.24)"
    assert "·" not in result


def test_format_shap_bar_empty_returns_empty_string():
    assert format_shap_bar({}) == ""


def test_format_shap_bar_sorted_by_abs_value():
    """Larger absolute value should appear first."""
    result = format_shap_bar({"tat_hours": 0.84, "patients_queued": 3.24})
    assert result.startswith("↑ Queue load")


def test_format_shap_bar_unknown_field_uses_title_case():
    result = format_shap_bar({"some_new_field": 1.5})
    assert "Some New Field" in result


def test_format_shap_bar_zero_value_positive_arrow():
    result = format_shap_bar({"patients_queued": 0.0})
    assert "↑" in result
    assert "(+0.00)" in result


# ─── build_alert_cards — empty ───────────────────────────────────────────────

def test_build_alert_cards_empty_returns_placeholder():
    html = build_alert_cards([])
    assert isinstance(html, str)
    assert _PLACEHOLDER in html


def test_build_alert_cards_empty_is_html():
    html = build_alert_cards([])
    assert "<div" in html


# ─── build_alert_cards — with alerts ─────────────────────────────────────────

def _make_alert(tick, alert_type="critical", facility="DHC-A", shap=None):
    return AlertRecord(
        tick=tick,
        facility_id=facility,
        network_id="NET-A",
        alert_type=alert_type,
        message=f"Test alert at tick {tick}",
        shap_contributions=shap or {"patients_queued": 1.0},
        severity="critical",
    )


def test_build_alert_cards_returns_html_string():
    html = build_alert_cards([_make_alert(4)])
    assert isinstance(html, str)
    assert "<div" in html


def test_build_alert_cards_most_recent_first():
    alerts = [_make_alert(4), _make_alert(10), _make_alert(7)]
    html = build_alert_cards(alerts)
    pos_10 = html.index("Tick 10")
    pos_7 = html.index("Tick 7")
    pos_4 = html.index("Tick 4")
    assert pos_10 < pos_7 < pos_4


def test_build_alert_cards_max_cards_respected():
    alerts = [_make_alert(i) for i in range(20)]
    html = build_alert_cards(alerts, max_cards=14)
    # Should contain at most 14 "Tick N" occurrences
    tick_count = html.count("Tick ")
    assert tick_count <= 14


def test_build_alert_cards_critical_colour():
    html = build_alert_cards([_make_alert(4, alert_type="critical")])
    assert "#dc2626" in html


def test_build_alert_cards_dto_advisory_colour():
    html = build_alert_cards([_make_alert(14, alert_type="dto_advisory")])
    assert "#fef3c7" in html
    assert "#92400e" in html


def test_build_alert_cards_bayesian_colour():
    html = build_alert_cards([_make_alert(6, alert_type="bayesian")])
    assert "#eff6ff" in html
    assert "#1e40af" in html


def test_build_alert_cards_recommendation_colour():
    html = build_alert_cards([_make_alert(7, alert_type="recommendation")])
    assert "#eff6ff" in html
    assert "#1e40af" in html


def test_build_alert_cards_contains_message():
    alert = _make_alert(4)
    html = build_alert_cards([alert])
    assert "Test alert at tick 4" in html


def test_build_alert_cards_contains_tick():
    html = build_alert_cards([_make_alert(4)])
    assert "Tick 4" in html


def test_build_alert_cards_contains_badge():
    html = build_alert_cards([_make_alert(4, alert_type="critical")])
    assert "CRITICAL" in html


def test_build_alert_cards_contains_shap():
    alert = _make_alert(4, shap={"patients_queued": 3.24, "tat_hours": 0.84})
    html = build_alert_cards([alert])
    assert "SHAP" in html
    assert "Queue load" in html


def test_build_alert_cards_deduplication():
    """Same tick + type + facility should only appear once."""
    alerts = [
        _make_alert(4, alert_type="critical", facility="DHC-A"),
        _make_alert(4, alert_type="critical", facility="DHC-A"),  # duplicate
    ]
    html = build_alert_cards(alerts)
    assert html.count("Tick 4") == 1


def test_build_alert_cards_different_facilities_not_deduped():
    """Same tick + type but different facility → both shown."""
    alerts = [
        _make_alert(4, alert_type="critical", facility="DHC-A"),
        _make_alert(4, alert_type="critical", facility="TL1-A"),
    ]
    html = build_alert_cards(alerts)
    assert html.count("Tick 4") == 2


def test_build_alert_cards_multiple_types():
    alerts = [
        _make_alert(4,  alert_type="critical"),
        _make_alert(14, alert_type="dto_advisory"),
        _make_alert(6,  alert_type="bayesian"),
    ]
    html = build_alert_cards(alerts)
    assert "CRITICAL" in html
    assert "DTO ADVISORY" in html
    assert "BAYESIAN" in html


# ─── Integration: load from pre-generated data ───────────────────────────────

def test_build_alert_cards_from_real_alerts():
    """Build cards from SC-01 pre-generated alerts JSON."""
    import json
    from pathlib import Path
    alerts_data = json.loads(Path("data/scenarios/sc-01_alerts.json").read_text())
    alerts = [
        AlertRecord(
            tick=a["tick"],
            facility_id=a["facility_id"],
            network_id=a["network_id"],
            alert_type=a["alert_type"],
            message=a["message"],
            shap_contributions=a["shap_contributions"],
            severity=a["severity"],
        )
        for a in alerts_data
    ]
    html = build_alert_cards(alerts, max_cards=14)
    assert isinstance(html, str)
    assert "<div" in html
    # SC-01 has 4 alerts; all should be shown (< 14)
    assert html.count("Tick ") == len(alerts)
