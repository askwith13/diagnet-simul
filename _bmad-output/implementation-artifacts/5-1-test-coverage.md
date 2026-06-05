---
status: review
baseline_commit: NO_VCS
---

# Story 5.1: Complete Test Suite to Coverage Gate

As a developer,
I want the full pytest suite to pass at ≥80% line coverage on core/ and generation/,
So that the team has a regression safety net before the hackathon demo.

## Acceptance Criteria

**AC1:** `uv run pytest --cov=core --cov=generation --cov-fail-under=80` exits 0 at ≥80% coverage
**AC2:** SC-01 golden fixture regression matches to 4 decimal places (ticks 0-4)

## Tasks/Subtasks

- [x] T1: Create core/data_generator.py (seed_baseline_states)
- [x] T2: Create tests/test_data_generator.py
- [x] T3: Verify coverage gate — 93.36% ≥ 80% ✅
- [x] T4: Verify AC2 (golden fixture test passes)

## Dev Notes

- Coverage is already 93% — no chase needed; gate is 80%
- core/data_generator.py: seed_baseline_states(networks_data, seed, noise_scale) → baseline FacilityStates
- test_data_generator.py: determinism (same seed → same output), 17 fields populated, 59 total facilities

## Dev Agent Record
### Implementation Plan
Coverage already at 93% before this story. Only missing piece: core/data_generator.py + tests/test_data_generator.py (required by story AC list). Added seed_baseline_states() with optional Gaussian noise, determinism tests, 19 passing tests. Coverage rose to 93.36% after adding the new module (100% covered).

### Completion Notes
- ✅ AC1: 93.36% coverage on core/ + generation/ (gate: 80%); exit 0
- ✅ AC1: All 7 listed test files present and passing (test_models, test_data_generator, test_config_contract, test_engine, test_shap_calculator, test_network_map, test_alerts)
- ✅ AC2: SC-01 golden fixture matches to 4dp for ticks 0-4
- ✅ 361/361 total tests green

Coverage breakdown:
- core/data_generator.py: 100%
- core/models.py: 100%
- generation/shap_calculator.py: 100%
- generation/scenario_config.py: 100%
- generation/engine.py: 88% (27 uncovered lines — mostly error branches)

## File List

- `core/data_generator.py` (created — seed_baseline_states, _make_facility_state, _noisy)
- `tests/test_data_generator.py` (created — 19 tests)

## Change Log

- 2026-06-05: Story 5.1 complete — 93.36% coverage; 19 data_generator tests; suite 361/361
