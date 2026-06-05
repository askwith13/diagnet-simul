---
status: review
baseline_commit: NO_VCS
---

# Story 1.3: Contract Tests (Red State)

As a developer,
I want contract tests written and failing before any YAML or simulation code exists,
So that the test suite defines the correctness contract before implementation begins.

## Acceptance Criteria

**AC1:**
**Given** tests/test_config_contract.py exists
**When** run with `uv run pytest tests/test_config_contract.py`
**Then** tests FAIL with FileNotFoundError (no YAML exists yet — intentional red state)
**And** the file contains test_alert_tokens_resolve_against_facility_state

**AC2:**
**Given** tests/conftest.py exists
**When** imported
**Then** provides fixtures: dummy_facility_state (17-field FacilityState), dummy_alert_record, dummy_tick_df (2-row DataFrame with all FlatTickSnapshot columns)

**AC3:**
**Given** tests/test_models.py already exists (Story 1.2)
**When** run
**Then** all 16 tests pass (no regression)

## Tasks/Subtasks

- [x] T1: Create tests/conftest.py with shared fixtures
- [x] T2: Create tests/test_config_contract.py (must fail — red state)
  - [x] T2.1: test_alert_tokens_resolve_against_facility_state
  - [x] T2.2: test_scenario_yamls_have_required_keys
  - [x] T2.3: test_shap_weights_match_per_tick_deltas
- [x] T3: Verify contract tests fail with FileNotFoundError
- [x] T4: Verify full suite (smoke + models) still passes

## Dev Notes

- Contract tests MUST fail in this story — that is the success criterion
- load_all_scenarios() raises FileNotFoundError if config/scenarios/ dir missing or empty
- Only test_config_contract.py should fail; test_models.py + test_smoke.py must remain green
- dummy_tick_df must include all 25 FlatTickSnapshot columns

## Dev Agent Record

### Implementation Plan
conftest.py provides 3 fixtures using FlatTickSnapshot.__annotations__ for dummy_tick_df column list. test_config_contract.py calls _load_all_scenarios() which raises FileNotFoundError — this is the red mechanism. 4 contract tests, all fail with FileNotFoundError as required. Added test_all_8_scenarios_present beyond the story minimum.

### Debug Log
No issues.

### Completion Notes
- ✅ 4 contract tests fail with FileNotFoundError (red state, as required)
- ✅ conftest.py: dummy_facility_state (17 fields), dummy_alert_record, dummy_tick_df (25-col DataFrame)
- ✅ smoke (7) + models (16) = 23 tests still green — no regressions

## File List

- `tests/conftest.py` (created — 3 shared fixtures)
- `tests/test_config_contract.py` (created — 4 contract tests, intentionally failing)

## Change Log

- 2026-06-05: Story 1.3 complete — contract tests in red state (4 failing FileNotFoundError); conftest.py with 3 fixtures; 23 non-contract tests green
