"""Core data contracts shared between generation pipeline and playback app.

This module is the single source of truth for all data shapes.
FlatTickSnapshot field names MUST match parquet column names exactly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    import pandas as pd


# ---------------------------------------------------------------------------
# FacilityState — 17 fields per PRD §5.1 + architecture.md daily_consumption
# ---------------------------------------------------------------------------

@dataclass
class FacilityState:
    """Single facility's state at one tick of the simulation."""

    # Throughput & queue
    patients_queued: float = 0.0
    cartridges: float = 0.0
    truenat_chips: float = 0.0
    travel_time_min: float = 0.0
    tat_hours: float = 0.0
    hr_on_shift: float = 0.0

    # Equipment
    machines: int = 0
    modules: int = 0
    samples_per_module_per_day: float = 0.0
    daily_consumption: float = 0.0  # cartridges consumed per day at current rate

    # Quality indicators (0–1)
    smear_positivity_rate: float = 0.0
    specimen_rejection_rate: float = 0.0
    referral_completion_rate: float = 0.0
    chw_available: int = 0

    # AI model outputs (0–1)
    bayesian_stockout_prob: float = 0.0
    cascade_dropout_risk: float = 0.0

    # Status badge
    status: str = "ok"  # ok | warning | critical | offline


# ---------------------------------------------------------------------------
# AlertRecord — one scripted alert with embedded SHAP contributions
# ---------------------------------------------------------------------------

@dataclass
class AlertRecord:
    """A single alert fired at a specific tick for a facility."""

    tick: int
    facility_id: str
    network_id: str
    alert_type: str          # critical | dto_advisory | bayesian | recommendation
    message: str
    shap_contributions: dict[str, float] = field(default_factory=dict)
    severity: str = "info"   # critical | high | medium | low | info


# ---------------------------------------------------------------------------
# FlatTickSnapshot — data contract between generation pipeline and app.
# Parquet column names MUST match these field names exactly (verified by
# tests/test_config_contract.py).
# ---------------------------------------------------------------------------

class FlatTickSnapshot(TypedDict):
    """One parquet row: one tick × one facility.
    3 identifier fields + 17 FacilityState fields + 5 derived metrics = 25 total.
    """

    # Identifiers
    tick: int
    facility_id: str
    network_id: str

    # FacilityState fields (17) — must stay in sync with FacilityState above
    patients_queued: float
    cartridges: float
    truenat_chips: float
    travel_time_min: float
    tat_hours: float
    hr_on_shift: float
    machines: int
    modules: int
    samples_per_module_per_day: float
    daily_consumption: float
    smear_positivity_rate: float
    specimen_rejection_rate: float
    referral_completion_rate: float
    chw_available: int
    bayesian_stockout_prob: float
    cascade_dropout_risk: float
    status: str

    # Derived metrics (5)
    betweenness_centrality: float
    pagerank: float
    bottleneck_score: float       # 0.6×betweenness + 0.4×pagerank
    effective_capacity_days: float  # cartridges / daily_consumption
    predicted_stockout_day: float   # NaN if no prediction


# ---------------------------------------------------------------------------
# ScenarioMeta — one entry in data/scenarios/metadata.json
# ---------------------------------------------------------------------------

class ScenarioMeta(TypedDict, total=False):
    """Metadata for one pre-computed scenario.

    Fields marked optional (total=False) may be absent in older metadata.json
    versions; callers should use .get() with defaults for those fields.
    """

    id: str
    display_name: str
    tick_count: int
    network_ids: list[str]
    primary_network: str              # network that the scenario primarily affects
    parquet_path: str
    alerts_path: str
    reroutes: list[list]              # [[src, dst], ...] from scenario YAML
    recommended_actions: dict[str, list[str]]  # facility_id -> [action, ...]


# ---------------------------------------------------------------------------
# ScenarioPayload — in-memory representation of one loaded scenario
# ---------------------------------------------------------------------------

class ScenarioPayload(TypedDict):
    """All data for one scenario, loaded at app startup into session_state."""

    tick_df: pd.DataFrame       # parquet rows: all ticks × all facilities
    alerts: list[AlertRecord]   # all alerts for this scenario
    metadata: ScenarioMeta


# ---------------------------------------------------------------------------
# safe_format — alert message interpolation with graceful missing-key fallback
# ---------------------------------------------------------------------------

class FacilityLayout(TypedDict):
    """Display metadata for one facility — sourced from networks.yaml at app startup."""
    display_name: str
    type: str        # hub | truenat | microscopy | chc
    x: float         # normalised canvas position [0, 1]
    y: float         # normalised canvas position [0, 1]


def safe_format(template: str, state_dict: dict[str, Any]) -> str:
    """Format a template string against state_dict.

    Uses str.format_map with a SafeDict so missing keys render as [key_name]
    rather than raising KeyError.  If a format spec (e.g. :.0f) is applied
    to a missing-key placeholder string, catches the resulting ValueError and
    falls back to a regex substitution that omits the format spec.
    """

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:
            return f"[{key}]"

    try:
        return template.format_map(_SafeDict(state_dict))
    except (ValueError, TypeError, KeyError):
        # Format spec applied to a placeholder string → plain substitution
        return re.sub(
            r"\{(\w+)(?:[^}]*)?\}",
            lambda m: str(state_dict.get(m.group(1), f"[{m.group(1)}]")),
            template,
        )
