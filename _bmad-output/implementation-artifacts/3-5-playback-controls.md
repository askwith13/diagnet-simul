---
status: review
baseline_commit: NO_VCS
---

# Story 3.5: Persistent Top Bar & Playback Controls

As a presenter,
I want fully functional Play/Pause/Rewind controls with a Playback Speed slider and tick counter,
So that I can control the demo narrative — pausing on key moments and advancing at the right pace.

## Acceptance Criteria

**AC1:** Play → IS_PLAYING=True → tick advances every interval_s seconds
**AC2:** Pause → IS_PLAYING=False → tick counter freezes within one rerun cycle
**AC3:** Rewind → TICK_CURSOR=0, IS_PLAYING=False, SELECTED_FACILITY=None; scenario_snapshots preserved
**AC4:** Speed=4× → advance every ~0.2s; per-tick data values unchanged (speed doesn't scale deltas)
**AC5:** At max_ticks-1 → IS_PLAYING=False; cursor stays at max_ticks-1

## Tasks/Subtasks

- [x] T1: Add apply_playback_step() to playback.py — encapsulates one-tick state transition
- [x] T2: Update app.py playback loop to use apply_playback_step()
- [x] T3: Write tests/test_playback_controls.py — state machine tests
- [x] T4: Full suite passes

## Dev Notes

- apply_playback_step(state, max_ticks, current_scenario, tick_df) → state (pure dict mutation, no Streamlit)
- Saves completed scenario to SCENARIO_SNAPSHOTS on end
- All 5 ACs testable through the state machine without running Streamlit

## Dev Agent Record
### Implementation Plan
apply_playback_step(state, max_ticks, current_scenario, tick_df) added to playback.py — reads IS_PLAYING/TICK_CURSOR/SCENARIO_SNAPSHOTS via session constants, mutates state dict, returns bool. app.py updated to call apply_playback_step() instead of inline logic. All 5 ACs tested via state machine without Streamlit.

### Completion Notes
- ✅ All 5 ACs verified via 22 state-machine tests
- ✅ apply_playback_step: advances tick, stops at end, saves snapshot, returns False when paused
- ✅ Speed slider confirmed data-agnostic (only affects sleep interval)
- ✅ Rewind confirmed preserves SCENARIO_SNAPSHOTS
- ✅ 22 tests; 249/249 total green

## File List

- `playback.py` (updated — added apply_playback_step)
- `app.py` (updated — uses apply_playback_step in playback loop)
- `tests/test_playback_controls.py` (created — 22 tests)

## Change Log

- 2026-06-05: Story 3.5 complete — apply_playback_step + state machine tests; 22 tests; suite 249/249
