---
status: review
baseline_commit: NO_VCS
---

# Story 3.4: App Startup & Data Loading

As a developer,
I want app.py to validate all pre-computed data at startup, load all 8 scenarios eagerly, and halt with a clear error if data is missing,
So that the demo never starts in a corrupt state and missing data is immediately actionable.

## Acceptance Criteria

**AC1:** app loads without error; session_state[SCENARIO_DATA] contains 8 ScenarioPayload entries
**AC2:** Missing parquet → st.error("Pre-computed data missing...") + st.stop(); no other content rendered
**AC3:** Scenario dropdown selection updates session_state[CURRENT_SCENARIO]; Tab 1 renders tick 0 of new scenario

## Tasks/Subtasks

- [x] T1: Create loader.py with load_scenario_payloads() and validate_data_exists()
- [x] T2: Create tabs/__init__.py + stub tabs (network, overview, facility, export placeholders)
- [x] T3: Write app.py (startup validation, eager load, tab skeleton, scenario selector)
- [x] T4: Write tests/test_loader.py
- [x] T5: Verify app.py starts: syntax OK, all non-Streamlit imports resolve
- [x] T6: Full suite passes

## Dev Notes

- Non-Streamlit logic in loader.py (testable); app.py is thin Streamlit wiring only
- validate_data_exists() returns list of missing paths (empty = all OK)
- load_scenario_payloads() reads parquet + alerts JSON → Dict[str, ScenarioPayload]
- GRAPH_CACHE in session_state stores {net_id: {layout, links}} from networks.yaml
- Tab content functions come in Stories 3.5, 3.6, 4.1, 4.2 — stubs only here

## Dev Agent Record
### Implementation Plan
loader.py (no Streamlit): load_metadata(), validate_data_exists(), load_scenario_payloads(). Testable with plain paths. app.py: startup block guarded by `if SCENARIO_DATA not in st.session_state` — runs once per session. GRAPH_CACHE stores {net_id: {layout, links}} loaded from networks.yaml. 4 tab stubs delegate to tabs/*.py. Playback loop at bottom: if IS_PLAYING → sleep → advance_tick → rerun. tabs/ has __init__.py + 4 stub modules with clear "coming in Story X" messages.

### Completion Notes
- ✅ load_scenario_payloads() loads all 8 scenarios with correct shapes
- ✅ validate_data_exists() detects missing parquets
- ✅ loader.py, session.py, playback.py all confirmed Streamlit-free
- ✅ app.py syntax OK; all non-Streamlit imports resolve
- ✅ 21 loader tests; 227/227 total green

## File List

- `loader.py` (created — load_metadata, validate_data_exists, load_scenario_payloads)
- `app.py` (updated — full startup, top bar, 4-tab skeleton, playback loop)
- `tabs/__init__.py` (created)
- `tabs/network.py`, `tabs/overview.py`, `tabs/facility.py`, `tabs/export.py` (stubs)
- `tests/test_loader.py` (created — 21 tests)

## Change Log

- 2026-06-05: Story 3.4 complete — loader.py + app.py startup; 21 tests; suite 227/227
