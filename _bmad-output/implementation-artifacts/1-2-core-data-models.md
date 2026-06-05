---
status: review
baseline_commit: NO_VCS
---

# Story 1.2: Core Data Models

As a developer,
I want all shared TypedDicts and dataclasses defined in core/models.py,
So that generation pipeline and playback app share a single, explicit data contract with no ambiguity.

## Acceptance Criteria

**AC1:**
**Given** `core/models.py` exists and is imported
**Then** FacilityState (17-field dataclass), AlertRecord, ScenarioMeta, ScenarioPayload, FlatTickSnapshot, safe_format() are all importable

**AC2:**
**Given** FacilityState is instantiated with all 17 fields
**When** `safe_format("{patients_queued:.0f} patients", state.__dict__)` is called
**Then** returns formatted string without raising

**AC3:**
**Given** safe_format is called with a missing key
**When** `safe_format("{nonexistent_field}", state.__dict__)` is called
**Then** returns "[nonexistent_field]" without raising

**AC4:**
**Then** FlatTickSnapshot field names exactly match intended parquet column names

## Tasks/Subtasks

- [x] T1: Create core/ package with models.py
  - [x] T1.1: Create core/__init__.py
  - [x] T1.2: Implement FacilityState dataclass (17 fields)
  - [x] T1.3: Implement AlertRecord dataclass
  - [x] T1.4: Implement FlatTickSnapshot TypedDict (25 fields: 3 ids + 17 facility + 5 derived)
  - [x] T1.5: Implement ScenarioMeta and ScenarioPayload TypedDicts
  - [x] T1.6: Implement safe_format()
- [x] T2: Write tests in tests/test_models.py
  - [x] T2.1: test_facility_state_has_17_fields
  - [x] T2.2: test_flat_tick_snapshot_field_count (25 fields)
  - [x] T2.3: test_safe_format_formats_known_field
  - [x] T2.4: test_safe_format_handles_missing_key
  - [x] T2.5: test_safe_format_handles_format_spec_on_missing_key
- [x] T3: Run full test suite — all pass

## Dev Notes

- FacilityState fields (17): patients_queued, cartridges, truenat_chips, travel_time_min, tat_hours, hr_on_shift, machines, modules, samples_per_module_per_day, daily_consumption, smear_positivity_rate, specimen_rejection_rate, referral_completion_rate, chw_available, bayesian_stockout_prob, cascade_dropout_risk, status
- FlatTickSnapshot adds: tick (int), facility_id (str), network_id (str) + 5 derived: betweenness_centrality, pagerank, bottleneck_score, effective_capacity_days, predicted_stockout_day
- safe_format uses str.format_map with _SafeDict fallback; catches ValueError/TypeError for format specs on missing keys and falls back to regex substitution
- generation/ must NEVER be imported by this module
- ScenarioPayload uses pd.DataFrame — pandas import required

## Dev Agent Record

### Implementation Plan
FacilityState as plain dataclass with defaults (all zero). AlertRecord with default_factory for shap_contributions dict. FlatTickSnapshot as TypedDict (25 fields: tick+facility_id+network_id + 17 FacilityState + 5 derived). ScenarioPayload uses TYPE_CHECKING guard for pd.DataFrame to avoid circular imports. safe_format uses _SafeDict.__missing__ + ValueError fallback to regex for format-spec-on-missing-key edge case.

### Debug Log
No issues.

### Completion Notes
- ✅ FacilityState: 17 fields, all verified by test_facility_state_field_names
- ✅ FlatTickSnapshot: 25 fields, FacilityState field names verified as subset via test_flat_tick_snapshot_facility_fields_match_facility_state
- ✅ safe_format handles format spec on missing key via ValueError catch + regex fallback
- ✅ 16 model tests + 7 smoke tests = 23 total, all green

## File List

- `core/__init__.py` (created)
- `core/models.py` (created — FacilityState, AlertRecord, FlatTickSnapshot, ScenarioMeta, ScenarioPayload, safe_format)
- `tests/test_models.py` (created — 16 tests)

## Change Log

- 2026-06-05: Story 1.2 complete — core/models.py with all 6 data contracts; 16 tests green; full suite 23/23
