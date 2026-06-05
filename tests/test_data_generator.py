"""Tests for core/data_generator.py — baseline state seeding."""
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from core.data_generator import seed_baseline_states
from core.models import FacilityState

NETWORKS_PATH = Path("config/networks.yaml")


@pytest.fixture(scope="module")
def networks_data() -> dict:
    return yaml.safe_load(NETWORKS_PATH.read_text())


@pytest.fixture(scope="module")
def baseline_states(networks_data) -> dict:
    return seed_baseline_states(networks_data, seed=42, noise_scale=0.0)


# ─── Structure ────────────────────────────────────────────────────────────────

def test_returns_5_networks(baseline_states):
    assert set(baseline_states.keys()) == {"NET-A", "NET-B", "NET-C", "NET-D", "NET-E"}


def test_net_a_has_14_facilities(baseline_states):
    assert len(baseline_states["NET-A"]) == 14


def test_net_b_has_11_facilities(baseline_states):
    assert len(baseline_states["NET-B"]) == 11


def test_net_c_has_13_facilities(baseline_states):
    assert len(baseline_states["NET-C"]) == 13


def test_net_d_has_9_facilities(baseline_states):
    assert len(baseline_states["NET-D"]) == 9


def test_net_e_has_12_facilities(baseline_states):
    assert len(baseline_states["NET-E"]) == 12


def test_total_59_facilities(baseline_states):
    total = sum(len(facs) for facs in baseline_states.values())
    assert total == 59


# ─── FacilityState quality ───────────────────────────────────────────────────

def test_all_values_are_facility_state(baseline_states):
    for net_id, facs in baseline_states.items():
        for fac_id, fs in facs.items():
            assert isinstance(fs, FacilityState), f"{net_id}/{fac_id} is not FacilityState"


def test_all_17_fields_populated(baseline_states):
    field_count = len(fields(FacilityState))
    assert field_count == 17
    for net_id, facs in baseline_states.items():
        for fac_id, fs in facs.items():
            for f in fields(FacilityState):
                val = getattr(fs, f.name)
                assert val is not None, f"{net_id}/{fac_id}.{f.name} is None"


def test_no_negative_count_fields(baseline_states):
    count_fields = [
        "patients_queued", "cartridges", "truenat_chips", "tat_hours",
        "hr_on_shift", "daily_consumption", "samples_per_module_per_day",
    ]
    for net_id, facs in baseline_states.items():
        for fac_id, fs in facs.items():
            for fname in count_fields:
                val = getattr(fs, fname)
                assert val >= 0, f"{net_id}/{fac_id}.{fname} = {val} (negative)"


def test_rate_fields_in_unit_range(baseline_states):
    rate_fields = [
        "smear_positivity_rate", "specimen_rejection_rate",
        "referral_completion_rate", "bayesian_stockout_prob", "cascade_dropout_risk",
    ]
    for net_id, facs in baseline_states.items():
        for fac_id, fs in facs.items():
            for fname in rate_fields:
                val = getattr(fs, fname)
                assert 0.0 <= val <= 1.0, f"{net_id}/{fac_id}.{fname} = {val} out of [0,1]"


def test_status_valid(baseline_states):
    valid = {"ok", "warning", "critical", "offline"}
    for net_id, facs in baseline_states.items():
        for fac_id, fs in facs.items():
            assert fs.status in valid, f"{net_id}/{fac_id}.status = '{fs.status}' not in {valid}"


def test_dhc_a_baseline_values(baseline_states):
    """DHC-A should match the YAML baseline from networks.yaml."""
    fs = baseline_states["NET-A"]["DHC-A"]
    assert fs.patients_queued == pytest.approx(42.0)
    assert fs.cartridges == pytest.approx(120.0)
    assert fs.tat_hours == pytest.approx(18.0)
    assert fs.daily_consumption == pytest.approx(8.0)
    assert fs.machines == 3
    assert fs.modules == 6
    assert fs.status == "ok"


def test_dhc_d_baseline_is_truenat_hub(baseline_states):
    """NET-D hub uses truenat_chips (not cartridges)."""
    fs = baseline_states["NET-D"]["DHC-D"]
    assert fs.truenat_chips > 0
    assert fs.cartridges == 0.0


# ─── Determinism ─────────────────────────────────────────────────────────────

def test_same_seed_produces_identical_output(networks_data):
    """Two calls with the same seed and noise must produce identical states."""
    s1 = seed_baseline_states(networks_data, seed=42, noise_scale=0.05)
    s2 = seed_baseline_states(networks_data, seed=42, noise_scale=0.05)
    for net_id in s1:
        for fac_id in s1[net_id]:
            fs1, fs2 = s1[net_id][fac_id], s2[net_id][fac_id]
            assert fs1.patients_queued == pytest.approx(fs2.patients_queued)
            assert fs1.tat_hours == pytest.approx(fs2.tat_hours)


def test_different_seeds_produce_different_noisy_output(networks_data):
    """Different seeds with noise should differ on at least some values."""
    s1 = seed_baseline_states(networks_data, seed=42, noise_scale=0.10)
    s2 = seed_baseline_states(networks_data, seed=99, noise_scale=0.10)
    any_diff = any(
        s1[net][fac].patients_queued != s2[net][fac].patients_queued
        for net in s1
        for fac in s1[net]
    )
    assert any_diff, "Different seeds produced identical outputs (noise not applied)"


def test_zero_noise_is_deterministic_without_seed(networks_data):
    """noise_scale=0.0 always returns exact baseline values regardless of seed."""
    s1 = seed_baseline_states(networks_data, seed=0,  noise_scale=0.0)
    s2 = seed_baseline_states(networks_data, seed=99, noise_scale=0.0)
    for net_id in s1:
        for fac_id in s1[net_id]:
            assert s1[net_id][fac_id].patients_queued == s2[net_id][fac_id].patients_queued


# ─── Noise application ────────────────────────────────────────────────────────

def test_noise_shifts_values(networks_data):
    """With noise, at least some values differ from the exact baseline."""
    exact = seed_baseline_states(networks_data, seed=42, noise_scale=0.0)
    noisy = seed_baseline_states(networks_data, seed=42, noise_scale=0.10)
    diffs = sum(
        1
        for net in exact
        for fac in exact[net]
        if exact[net][fac].patients_queued != noisy[net][fac].patients_queued
    )
    assert diffs > 0, "Noise had no effect on baseline values"


def test_noise_keeps_values_non_negative(networks_data):
    """Even with large noise, no count field should go negative."""
    states = seed_baseline_states(networks_data, seed=7, noise_scale=0.30)
    for net_id, facs in states.items():
        for fac_id, fs in facs.items():
            assert fs.patients_queued >= 0.0
            assert fs.cartridges >= 0.0
            assert fs.tat_hours >= 0.0
