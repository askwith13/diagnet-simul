---
status: review
baseline_commit: NO_VCS
---

# Story 2.5: SHAP Calculator

As a developer,
I want generation/shap_calculator.py with compute_shap() and generate_alert_shap(),
So that every alert has mathematically consistent, readable SHAP explanations.

## Acceptance Criteria

**AC1:** `compute_shap(delta=1.8, weight=0.45)` returns 0.81 exactly (delta × weight)
**AC2:** `generate_alert_shap` for SC-01 tick 4 DHC-A returns:
  patients_queued=3.24, tat_hours=0.84, cascade_dropout_risk=0.032 (±0.01)
  (formula: per_tick_delta × weight × tick, sorted by |shap_f| desc, top-5)
**AC3:** Facility not in per_tick_deltas → returns empty dict
**AC4:** engine.py updated to use shap_calculator; inline _compute_shap removed

## Tasks/Subtasks

- [x] T1: Create generation/shap_calculator.py
- [x] T2: Update engine.py to import and use shap_calculator (remove _compute_shap)
- [x] T3: Write tests/test_shap_calculator.py
- [x] T4: Full suite passes — no regressions

## Dev Notes

- formula: shap_f = delta × weight × tick (tick is 0-indexed; at tick=4, ticks_elapsed=4)
- current engine.py uses (tick+1) — incorrect; fix to tick during this story
- generate_alert_shap signature: (alert_config: AlertConfig, facility_state: FacilityState, scenario_config: ScenarioConfig) -> dict[str, float]
- facility_state param accepted but not used (reserved for production fastshap upgrade)
- return top-5 by |shap_f| descending

## Dev Agent Record

### Implementation Plan
compute_shap = delta × weight (pure function, no ticks). generate_alert_shap = compute_shap × tick for each delta field; sorted by abs desc, top-5; empty dict if facility not in per_tick_deltas. facility_state accepted but unused (reserved for production fastshap). Engine updated: removed inline _compute_shap, imported generate_alert_shap, kept tick (not tick+1) formula. Integration test confirms engine alerts match shap_calculator output.

### Completion Notes
- ✅ compute_shap(1.8, 0.45) = 0.81 exactly
- ✅ Worked example: patients_queued=3.24, tat_hours=0.84, dropout=0.032 at tick 4
- ✅ Empty dict for unaffected facility
- ✅ Engine now uses shap_calculator (inline code removed)
- ✅ 13 new SHAP tests; 106/106 total green

## File List

- `generation/shap_calculator.py` (created — compute_shap, generate_alert_shap)
- `generation/engine.py` (updated — removed _compute_shap, imports shap_calculator)
- `tests/test_shap_calculator.py` (created — 13 tests)

## Change Log

- 2026-06-05: Story 2.5 complete — shap_calculator.py; 13 tests; suite 106/106
