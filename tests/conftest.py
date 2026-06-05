"""Shared pytest fixtures for all DiagNet test modules."""
import pandas as pd
import pytest

from core.models import AlertRecord, FacilityState, FlatTickSnapshot


@pytest.fixture
def dummy_facility_state() -> FacilityState:
    """A fully-populated FacilityState representing a healthy urban hub at baseline."""
    return FacilityState(
        patients_queued=42.0,
        cartridges=120.0,
        truenat_chips=15.0,
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


@pytest.fixture
def dummy_alert_record() -> AlertRecord:
    """A CRITICAL alert at tick 4 for DHC-A with two SHAP contributions."""
    return AlertRecord(
        tick=4,
        facility_id="DHC-A",
        network_id="NET-A",
        alert_type="critical",
        message="DHC queue critical: 58 patients, TAT 34h",
        shap_contributions={"patients_queued": 3.24, "tat_hours": 0.84},
        severity="critical",
    )


@pytest.fixture
def dummy_tick_df() -> pd.DataFrame:
    """A 2-row DataFrame with all 25 FlatTickSnapshot columns at tick 0 and tick 1."""
    columns = list(FlatTickSnapshot.__annotations__.keys())

    base_row: dict = {col: 0 for col in columns}
    base_row.update(
        {
            "facility_id": "DHC-A",
            "network_id": "NET-A",
            "status": "ok",
            "betweenness_centrality": 0.42,
            "pagerank": 0.18,
            "bottleneck_score": 0.32,
            "effective_capacity_days": 15.0,
            "predicted_stockout_day": float("nan"),
        }
    )

    row0 = {**base_row, "tick": 0}
    row1 = {**base_row, "tick": 1, "patients_queued": 43.8}
    return pd.DataFrame([row0, row1])
