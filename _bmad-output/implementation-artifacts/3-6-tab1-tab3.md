---
status: review
baseline_commit: NO_VCS
---

# Story 3.6: Tab 1 — Network Map + Alert Panel & Tab 3 — Facility Detail

As a Lab Supervisor, DTO, and Funder,
I want the network map with alert panel and the facility SHAP waterfall to work,
So that the primary demo moments are fully functional.

## Acceptance Criteria

**AC1:** Tab 1 at tick 0 — network map renders with correct tier sizes/colours; alert panel shows placeholder; metrics bar shows 5 cards
**AC2:** At tick 4 in SC-01 — DHC-A turns red with outer ring; alert panel shows CRITICAL card with SHAP
**AC3:** At tick 7 — blue dashed reroute edges appear (MC2-A→TL2-A, CHC2-A→TL2-A)
**AC4:** Node click → session_state[SELECTED_FACILITY] = facility_id
**AC5:** Tab 3 with SELECTED_FACILITY — facility header, 4 time-series charts with threshold lines, SHAP waterfall, recommended actions
**AC6:** Tab 3 without selection — "Click any node on the Network Map to open facility detail."

## Tasks/Subtasks

- [x] T1: Update ScenarioMeta to include reroutes + recommended_actions; update loader.py to load them from YAML
- [x] T2: Implement tabs/network.py — render_network_tab, compute_metrics, get_active_reroutes
- [x] T3: Implement tabs/facility.py — render_facility_tab, build_time_series_figure, build_shap_waterfall_figure, get_recommended_actions
- [x] T4: Write tests/test_tabs.py covering pure helper functions
- [x] T5: Full suite passes

## Dev Notes

- reroutes active when tick >= first recommendation alert tick for the scenario
- SHAP waterfall shows shap_contributions from most recent alert for selected facility up to current tick
- time-series charts show all ticks from tick_df up to current tick
- Threshold lines: patients_queued (35/55), cartridges (25/10), tat_hours (24/36), cascade_dropout_risk (0.35/0.60)
- render_* functions use Streamlit; helper functions (compute_metrics, build_*) are pure and testable

## Dev Agent Record
### Implementation Plan
ScenarioMeta extended with reroutes + recommended_actions (total=False to keep backwards compat). loader.py reads YAML alongside parquet to populate these fields. tabs/network.py: compute_metrics() filters by network_id; get_active_reroutes() activates at first recommendation tick. tabs/facility.py: pure Plotly functions (build_time_series_figure, build_shap_waterfall_figure) + testable helpers. render_facility_tab handles None selected_facility with placeholder. Fixed f-string backslash escape in facility tab status colour.

### Completion Notes
- ✅ reroutes + recommended_actions loaded into payload for all 8 scenarios
- ✅ get_active_reroutes correct: None before tick 7, [[MC2-A,TL2-A],[CHC2-A,TL2-A]] after
- ✅ SHAP waterfall: positive=blue, negative=red, title contains "Approximate"
- ✅ time-series: respects up_to_tick; threshold lines present
- ✅ 32 tab tests; 281/281 total green

## File List

- `core/models.py` (updated — ScenarioMeta with reroutes + recommended_actions)
- `loader.py` (updated — loads reroutes/recommended_actions from YAML)
- `tabs/network.py` (implemented — render_network_tab, compute_metrics, get_active_reroutes)
- `tabs/facility.py` (implemented — render_facility_tab + pure helper functions)
- `tests/test_tabs.py` (created — 32 tests)

## Change Log

- 2026-06-05: Story 3.6 complete — Tab 1 + Tab 3 functional; 32 tests; suite 281/281
