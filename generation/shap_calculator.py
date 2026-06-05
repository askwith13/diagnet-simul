"""SHAP approximation for alert contributions — build-time only.

Algorithm (PRD §7):
    shap_f = per_tick_delta × shap_weight × tick

where `tick` is 0-indexed (tick=4 means 4 ticks have elapsed since baseline).

All SHAP displays in the app are labelled "Approximate · simulation mode".
"""
from __future__ import annotations

from core.models import FacilityState
from generation.scenario_config import AlertConfig, ScenarioConfig


def compute_shap(delta: float, weight: float) -> float:
    """Base SHAP unit: contribution of one field for one tick.

    Args:
        delta: per_tick_delta for the field (from scenario YAML).
        weight: shap_weight for the field (from scenario YAML).

    Returns:
        delta × weight (the per-tick contribution before multiplying by elapsed ticks).
    """
    return delta * weight


def generate_alert_shap(
    alert_config: AlertConfig,
    facility_state: FacilityState,  # noqa: ARG001 — reserved for production fastshap
    scenario_config: ScenarioConfig,
) -> dict[str, float]:
    """Compute SHAP contributions for one alert.

    Formula: shap_f = per_tick_delta × shap_weight × tick

    Returns the top-5 contributions sorted by |shap_f| descending.
    Returns an empty dict if the alert's facility has no per_tick_deltas.

    Args:
        alert_config: The alert being explained (provides tick and facility_id).
        facility_state: Current FacilityState (reserved — not used in stub).
        scenario_config: Scenario providing per_tick_deltas and shap_weights.
    """
    fac_id = alert_config.facility
    if fac_id not in scenario_config.per_tick_deltas:
        return {}

    deltas = scenario_config.per_tick_deltas[fac_id]
    weights = scenario_config.shap_weights
    tick = alert_config.tick

    contributions: dict[str, float] = {}
    for field_name, delta in deltas.items():
        weight = weights.get(field_name, 0.0)
        contributions[field_name] = compute_shap(delta, weight) * tick

    top5 = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:5]
    return dict(top5)
