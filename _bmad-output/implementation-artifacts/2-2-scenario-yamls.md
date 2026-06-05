---
status: review
baseline_commit: NO_VCS
---

# Story 2.2: Scenario YAMLs — All 8 Scenarios

As a developer,
I want all 8 scenario YAML files with alert sequences matching PRD §6.2,
So that the generation pipeline can produce all pre-computed outputs without hardcoded values.

## Acceptance Criteria

**AC1:** sc-01.yaml through sc-08.yaml exist with: name, primary_network, max_ticks, affected_facilities, per_tick_deltas, shap_weights, reroutes, alerts, recommended_actions
**AC2:** SC-08 includes initial_states block with post-crisis baselines for all 5 networks
**AC3:** Every alert msg token resolves against FacilityState.__dict__
**AC4:** test_config_contract.py — all 4 tests GREEN

## Tasks/Subtasks

- [x] T1: Create config/scenarios/ directory
- [x] T2: Write sc-01 through sc-08 YAML files
- [x] T3: Verify contract tests turn green
- [x] T4: Full test suite passes

## Dev Notes

- Valid FacilityState token names: patients_queued, cartridges, truenat_chips, travel_time_min, tat_hours, hr_on_shift, machines, modules, samples_per_module_per_day, daily_consumption, smear_positivity_rate, specimen_rejection_rate, referral_completion_rate, chw_available, bayesian_stockout_prob, cascade_dropout_risk, status
- No facility names in msg tokens — those are static text
- SC-08 per_tick_deltas are negative (recovery direction)
- recommended_actions: per-facility list of 3 pre-authored action strings

## Dev Agent Record

### Implementation Plan
8 YAML files covering all scenarios from PRD §6.2 alert sequences. Alert msgs use only FacilityState field tokens. SC-08 has initial_states for all 5 networks in post-crisis condition + negative per_tick_deltas for recovery. shap_weights initially missed cascade_dropout_risk (SC-02), tat_hours (SC-04, SC-08), bayesian_stockout_prob (SC-06), daily_consumption (SC-07) — fixed by systematic scan before final test run.

### Completion Notes
- ✅ All 4 contract tests GREEN (were red since Story 1.3)
- ✅ All 8 scenarios present, required keys valid, tokens resolve, shap_weights complete
- ✅ SC-08 has initial_states + impact_metrics + negative recovery deltas
- ✅ 43/43 tests passing

## File List

- `config/scenarios/sc-01.yaml` (created)
- `config/scenarios/sc-02.yaml` (created)
- `config/scenarios/sc-03.yaml` (created)
- `config/scenarios/sc-04.yaml` (created)
- `config/scenarios/sc-05.yaml` (created)
- `config/scenarios/sc-06.yaml` (created)
- `config/scenarios/sc-07.yaml` (created)
- `config/scenarios/sc-08.yaml` (created)

## Change Log

- 2026-06-05: Story 2.2 complete — all 8 scenario YAMLs; contract tests GREEN; suite 43/43
