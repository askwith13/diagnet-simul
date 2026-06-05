---
status: review
baseline_commit: NO_VCS
---

# Story 3.3: Session State & Playback Engine

As a developer,
I want session.py and playback.py to define session_state keys as constants and implement the tick cursor loop,
So that no module uses raw string keys and the playback logic is testable in isolation.

## Acceptance Criteria

**AC1:** session.py exports 8 key constants (SCENARIO_DATA, CURRENT_SCENARIO, TICK_CURSOR, IS_PLAYING, SELECTED_FACILITY, SCENARIO_SNAPSHOTS, GRAPH_CACHE, PERF_LOG) all equal to their snake_case name
**AC2:** init_session_state(scenario_data) initialises TICK_CURSOR=0, IS_PLAYING=False, SELECTED_FACILITY=None
**AC3:** get_interval_s(0.5)=1.6, get_interval_s(1.0)=0.8, get_interval_s(2.0)=0.4, get_interval_s(4.0)=0.2
**AC4:** advance_tick(34, 35)=34 (bounds-checked); advance_tick(10, 35)=11

## Tasks/Subtasks

- [x] T1: Write session.py
- [x] T2: Write playback.py
- [x] T3: Write tests/test_session_playback.py
- [x] T4: Full suite passes

## Dev Notes

- init_session_state(scenario_data, state=None) → dict; accepts dict-like for testability (no Streamlit import needed)
- get_interval_s formula: 0.8 / speed_multiplier
- advance_tick: min(current_tick + 1, max_ticks - 1) — never exceeds max_ticks-1
- No Streamlit import in session.py or playback.py (pure Python)

## Dev Agent Record
### Implementation Plan
session.py: 8 string constants + init_session_state(scenario_data, state=None). Idempotent (preserves existing keys). Returns the state dict for testability without Streamlit. playback.py: get_interval_s = 0.8/speed (clamps on zero). advance_tick = min(tick+1, max_ticks-1). is_at_end helper. No Streamlit imports in either module.

### Completion Notes
- ✅ All 8 constants equal their snake_case names
- ✅ init_session_state idempotent; testable with plain dict
- ✅ get_interval_s matches architecture: 0.5×→1.6s, 1×→0.8s, 2×→0.4s, 4×→0.2s
- ✅ advance_tick bounds-checked; never exceeds max_ticks-1
- ✅ 30 tests; 206/206 total green

## File List

- `session.py` (created — 8 key constants + init_session_state)
- `playback.py` (created — get_interval_s, advance_tick, is_at_end)
- `tests/test_session_playback.py` (created — 30 tests)

## Change Log

- 2026-06-05: Story 3.3 complete — session.py + playback.py; 30 tests; suite 206/206
