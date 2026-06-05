"""Baseline state generator — seeds initial FacilityState objects from networks.yaml.

These are deterministic baseline states without scenario deltas. The generation
engine reads baselines directly for performance; this module provides a standalone
helper for testing and direct use.
"""
from __future__ import annotations

import numpy as np

from core.models import FacilityState


def seed_baseline_states(
    networks_data: dict,
    seed: int = 42,
    noise_scale: float = 0.0,
) -> dict[str, dict[str, FacilityState]]:
    """Create FacilityState objects from network baseline configurations.

    Args:
        networks_data: Parsed networks.yaml dict.
        seed: Random seed for stochastic noise (used only when noise_scale > 0).
        noise_scale: Fraction of baseline value to use as Gaussian noise σ.
                     0.0 = no noise (deterministic). 0.05 = ±5% noise.

    Returns:
        Dict[network_id, Dict[facility_id, FacilityState]] — baseline states
        for all networks and facilities in networks_data.
    """
    rng = np.random.default_rng(seed) if noise_scale > 0.0 else None
    result: dict[str, dict[str, FacilityState]] = {}

    for net_id, net_data in networks_data["networks"].items():
        result[net_id] = {}
        for fac_id, fac_data in net_data["facilities"].items():
            baseline = fac_data["baseline"]
            result[net_id][fac_id] = _make_facility_state(baseline, rng, noise_scale)

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _noisy(value: float, rng: np.random.Generator | None, scale: float) -> float:
    """Return value + optional Gaussian noise; floored at 0."""
    if rng is None or scale == 0.0 or value == 0.0:
        return value
    return max(0.0, value + float(rng.normal(0, scale * abs(value))))


def _make_facility_state(
    baseline: dict,
    rng: np.random.Generator | None,
    noise_scale: float,
) -> FacilityState:
    """Construct a FacilityState from a baseline dict with optional noise."""

    def flt(key: str, default: float = 0.0) -> float:
        return _noisy(float(baseline.get(key, default)), rng, noise_scale)

    def integer(key: str, default: int = 0) -> int:
        return int(baseline.get(key, default))

    return FacilityState(
        patients_queued=flt("patients_queued"),
        cartridges=flt("cartridges"),
        truenat_chips=flt("truenat_chips"),
        travel_time_min=flt("travel_time_min"),
        tat_hours=flt("tat_hours"),
        hr_on_shift=flt("hr_on_shift"),
        machines=integer("machines"),
        modules=integer("modules"),
        samples_per_module_per_day=flt("samples_per_module_per_day"),
        daily_consumption=flt("daily_consumption"),
        smear_positivity_rate=flt("smear_positivity_rate"),
        specimen_rejection_rate=flt("specimen_rejection_rate"),
        referral_completion_rate=flt("referral_completion_rate"),
        chw_available=integer("chw_available"),
        bayesian_stockout_prob=flt("bayesian_stockout_prob"),
        cascade_dropout_risk=flt("cascade_dropout_risk"),
        status=str(baseline.get("status", "ok")),
    )
