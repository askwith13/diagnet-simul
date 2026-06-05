"""Tests for core/models.py — data contracts."""
from dataclasses import fields

import pytest

from core.models import (
    AlertRecord,
    FacilityState,
    FlatTickSnapshot,
    ScenarioMeta,
    ScenarioPayload,
    safe_format,
)


# ---------------------------------------------------------------------------
# FacilityState
# ---------------------------------------------------------------------------

def test_facility_state_has_17_fields():
    assert len(fields(FacilityState)) == 17


def test_facility_state_default_status_is_ok():
    fs = FacilityState()
    assert fs.status == "ok"


def test_facility_state_field_names():
    expected = {
        "patients_queued", "cartridges", "truenat_chips", "travel_time_min",
        "tat_hours", "hr_on_shift", "machines", "modules",
        "samples_per_module_per_day", "daily_consumption",
        "smear_positivity_rate", "specimen_rejection_rate",
        "referral_completion_rate", "chw_available",
        "bayesian_stockout_prob", "cascade_dropout_risk", "status",
    }
    actual = {f.name for f in fields(FacilityState)}
    assert actual == expected


def test_facility_state_instantiation():
    fs = FacilityState(
        patients_queued=42.0,
        cartridges=120.0,
        truenat_chips=0.0,
        travel_time_min=55.0,
        tat_hours=18.0,
        hr_on_shift=8.0,
        machines=3,
        modules=6,
        samples_per_module_per_day=28.0,
        daily_consumption=8.0,
        smear_positivity_rate=0.15,
        specimen_rejection_rate=0.05,
        referral_completion_rate=0.85,
        chw_available=2,
        bayesian_stockout_prob=0.12,
        cascade_dropout_risk=0.08,
        status="ok",
    )
    assert fs.patients_queued == 42.0
    assert fs.daily_consumption == 8.0
    assert fs.status == "ok"


# ---------------------------------------------------------------------------
# FlatTickSnapshot
# ---------------------------------------------------------------------------

def test_flat_tick_snapshot_field_count():
    # 3 identifiers + 17 FacilityState fields + 5 derived metrics = 25
    assert len(FlatTickSnapshot.__annotations__) == 25


def test_flat_tick_snapshot_has_identifier_fields():
    annotations = FlatTickSnapshot.__annotations__
    assert "tick" in annotations
    assert "facility_id" in annotations
    assert "network_id" in annotations


def test_flat_tick_snapshot_has_derived_metrics():
    annotations = FlatTickSnapshot.__annotations__
    assert "betweenness_centrality" in annotations
    assert "pagerank" in annotations
    assert "bottleneck_score" in annotations
    assert "effective_capacity_days" in annotations
    assert "predicted_stockout_day" in annotations


def test_flat_tick_snapshot_facility_fields_match_facility_state():
    """FlatTickSnapshot facility fields must exactly match FacilityState field names."""
    facility_state_names = {f.name for f in fields(FacilityState)}
    snapshot_annotations = set(FlatTickSnapshot.__annotations__.keys())
    # All FacilityState fields must appear in FlatTickSnapshot
    assert facility_state_names.issubset(snapshot_annotations)


# ---------------------------------------------------------------------------
# AlertRecord
# ---------------------------------------------------------------------------

def test_alert_record_instantiation():
    alert = AlertRecord(
        tick=4,
        facility_id="DHC-A",
        network_id="NET-A",
        alert_type="critical",
        message="DHC queue critical: 58 patients",
        shap_contributions={"patients_queued": 3.24, "tat_hours": 0.84},
        severity="critical",
    )
    assert alert.tick == 4
    assert alert.shap_contributions["patients_queued"] == 3.24


def test_alert_record_default_shap_is_empty_dict():
    alert = AlertRecord(
        tick=0, facility_id="X", network_id="NET-A",
        alert_type="info", message="test",
    )
    assert alert.shap_contributions == {}


# ---------------------------------------------------------------------------
# safe_format
# ---------------------------------------------------------------------------

def test_safe_format_formats_known_field():
    fs = FacilityState(patients_queued=58.0, tat_hours=34.0)
    result = safe_format("{patients_queued:.0f} patients", fs.__dict__)
    assert result == "58 patients"


def test_safe_format_formats_multiple_known_fields():
    fs = FacilityState(patients_queued=58.0, tat_hours=34.0)
    result = safe_format(
        "DHC queue critical: {patients_queued:.0f} patients, TAT {tat_hours:.0f}h",
        fs.__dict__,
    )
    assert result == "DHC queue critical: 58 patients, TAT 34h"


def test_safe_format_handles_missing_key_no_spec():
    fs = FacilityState()
    result = safe_format("{nonexistent_field}", fs.__dict__)
    assert result == "[nonexistent_field]"


def test_safe_format_handles_missing_key_with_format_spec():
    """Missing key with a format spec should not raise — returns [key_name]."""
    fs = FacilityState()
    result = safe_format("{nonexistent_field:.0f}", fs.__dict__)
    assert result == "[nonexistent_field]"


def test_safe_format_plain_text_unchanged():
    result = safe_format("No fields here", {})
    assert result == "No fields here"


def test_safe_format_mixed_known_and_missing():
    fs = FacilityState(patients_queued=10.0)
    result = safe_format("{patients_queued:.0f} / {missing}", fs.__dict__)
    assert result == "10 / [missing]"
