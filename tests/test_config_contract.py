"""Contract tests — alert message tokens vs FacilityState fields.

EXPECTED STATE (Story 1.3):  FAILING — config/scenarios/*.yaml do not exist yet.
BECOMES PASSING (green) after Story 2.2 creates all 8 scenario YAML files.

These tests define the correctness contract before implementation begins.
"""
from __future__ import annotations

import re
from dataclasses import fields
from pathlib import Path

import yaml

from core.models import FacilityState

SCENARIOS_DIR = Path("config/scenarios")
REQUIRED_TOP_LEVEL_KEYS = {
    "name",
    "primary_network",
    "max_ticks",
    "affected_facilities",
    "per_tick_deltas",
    "shap_weights",
    "alerts",
}


def _load_all_scenarios() -> list[dict]:
    """Load all scenario YAML files.

    Raises FileNotFoundError if config/scenarios/ is absent or empty — this
    is the expected failure mode in Story 1.3 (red state).
    """
    if not SCENARIOS_DIR.exists():
        raise FileNotFoundError(
            f"Scenario config directory not found: {SCENARIOS_DIR}\n"
            "Create config/scenarios/*.yaml files (Story 2.2) to make these tests pass."
        )
    yaml_files = sorted(SCENARIOS_DIR.glob("*.yaml"))
    if not yaml_files:
        raise FileNotFoundError(
            f"No *.yaml files found in {SCENARIOS_DIR}\n"
            "Create config/scenarios/sc-01.yaml … sc-08.yaml (Story 2.2)."
        )
    return [(p.stem, yaml.safe_load(p.read_text())) for p in yaml_files]


def _extract_tokens(msg: str) -> set[str]:
    """Return all {token_name} placeholders from a format string."""
    return {m.group(1) for m in re.finditer(r"\{(\w+)(?:[^}]*)?\}", msg)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_alert_tokens_resolve_against_facility_state():
    """Every {token} in every alert msg must be a FacilityState field name.

    RED in Story 1.3 (no YAML) → GREEN after Story 2.2.
    """
    facility_fields = {f.name for f in fields(FacilityState)}
    scenarios = _load_all_scenarios()

    errors: list[str] = []
    for stem, scenario in scenarios:
        scenario_name = scenario.get("name", stem)
        for alert in scenario.get("alerts", []):
            msg = alert.get("msg", "")
            for token in _extract_tokens(msg):
                if token not in facility_fields:
                    errors.append(
                        f"[{scenario_name}] alert msg '{msg}' "
                        f"references unknown FacilityState field '{token}'"
                    )

    assert not errors, "\n" + "\n".join(errors)


def test_scenario_yamls_have_required_keys():
    """Every scenario YAML must contain all required top-level keys.

    RED in Story 1.3 → GREEN after Story 2.2.
    """
    scenarios = _load_all_scenarios()

    for stem, scenario in scenarios:
        missing = REQUIRED_TOP_LEVEL_KEYS - set(scenario.keys())
        assert not missing, (
            f"Scenario '{scenario.get('name', stem)}' missing required keys: {missing}"
        )


def test_shap_weights_match_per_tick_deltas():
    """shap_weights must contain a key for every field in per_tick_deltas.

    RED in Story 1.3 → GREEN after Story 2.2.
    """
    scenarios = _load_all_scenarios()

    for stem, scenario in scenarios:
        name = scenario.get("name", stem)
        deltas: dict = scenario.get("per_tick_deltas", {})
        weights: dict = scenario.get("shap_weights", {})

        for facility_deltas in deltas.values():
            for field_name in facility_deltas:
                assert field_name in weights, (
                    f"Scenario '{name}': per_tick_delta field '{field_name}' "
                    f"has no matching entry in shap_weights"
                )


def test_all_8_scenarios_present():
    """Exactly 8 scenario YAMLs must exist (sc-01 through sc-08).

    RED in Story 1.3 → GREEN after Story 2.2.
    """
    scenarios = _load_all_scenarios()
    assert len(scenarios) == 8, (
        f"Expected 8 scenario YAMLs, found {len(scenarios)}: "
        f"{[s for s, _ in scenarios]}"
    )
