---
status: review
baseline_commit: NO_VCS
---

# Story 2.3: Scenario Config Loader & Validator

As a developer,
I want generation/scenario_config.py to load and validate scenario YAMLs into typed Python objects,
So that the generation engine receives structured, validated config with no raw dict access.

## Acceptance Criteria

**AC1:** `load_scenario_yaml("config/scenarios/sc-01.yaml")` returns a populated ScenarioConfig dataclass
**AC2:** `validate_config(config, network_facility_ids)` raises descriptive ValueError for unknown facility IDs
**AC3:** `validate_config` raises if shap_weights keys don't cover all per_tick_delta field names
**AC4:** Error message names the offending facility/field and scenario

## Tasks/Subtasks

- [x] T1: Create generation/ package
  - [x] T1.1: generation/__init__.py
  - [x] T1.2: generation/scenario_config.py — dataclasses + loaders + validate_config()
- [x] T2: Write tests/test_scenario_config.py
- [x] T3: Full suite — 43 existing + new tests all pass

## Dev Notes

- generation/ is build-time only; never imported by app.py, viz/, or tabs/
- ScenarioConfig fields: name, primary_network, max_ticks, affected_facilities, per_tick_deltas, shap_weights, reroutes, alerts (list[AlertConfig]), recommended_actions, initial_states (SC-08 only), impact_metrics (SC-08 only), scenario_id
- AlertConfig fields: tick, type, severity, recipient, facility, msg
- load_networks_yaml() returns Dict[str, Set[str]] — network_id -> set of facility_ids
- validate_config() receives ScenarioConfig + set of all known facility_ids
- Use plain dataclasses (not pydantic) — consistent with core/models.py

## Dev Agent Record

### Implementation Plan
Plain dataclasses (ScenarioConfig, AlertConfig) — consistent with core/models.py. load_networks_yaml() returns Dict[str, Set[str]] for network→facilities. validate_config() checks 3 constraints with descriptive errors naming scenario + offending value. load_all_scenarios() returns sorted dict keyed by scenario_id. Optional fields (initial_states, impact_metrics) handled with None default for non-SC-08 scenarios.

### Completion Notes
- ✅ ScenarioConfig + AlertConfig dataclasses with all YAML fields
- ✅ load_scenario_yaml, load_all_scenarios, load_networks_yaml, all_facility_ids, validate_config all implemented
- ✅ validate_config passes for all 8 real scenarios
- ✅ 22 new tests; 65/65 total green

## File List

- `generation/__init__.py` (created)
- `generation/scenario_config.py` (created — ScenarioConfig, AlertConfig, loaders, validate_config)
- `tests/test_scenario_config.py` (created — 22 tests)

## Change Log

- 2026-06-05: Story 2.3 complete — generation/scenario_config.py; 22 tests green; suite 65/65
