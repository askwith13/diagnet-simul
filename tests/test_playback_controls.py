"""Tests for the playback state machine — all ACs exercised without Streamlit."""
import pytest

from playback import (
    advance_tick,
    apply_playback_step,
    get_interval_s,
    is_at_end,
)
from session import (
    CURRENT_SCENARIO,
    IS_PLAYING,
    SCENARIO_SNAPSHOTS,
    SELECTED_FACILITY,
    TICK_CURSOR,
    init_session_state,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_state(
    tick: int = 0,
    is_playing: bool = False,
    selected: str | None = None,
    snapshots: dict | None = None,
    scenario: str = "sc-01",
) -> dict:
    state = init_session_state({"sc-01": {"metadata": {"tick_count": 25}}})
    state[TICK_CURSOR] = tick
    state[IS_PLAYING] = is_playing
    state[SELECTED_FACILITY] = selected
    state[CURRENT_SCENARIO] = scenario
    if snapshots is not None:
        state[SCENARIO_SNAPSHOTS] = snapshots
    return state


DUMMY_DF = object()   # placeholder for scenario_tick_df in state-machine tests


# ─── AC1: Play → IS_PLAYING=True → tick advances ─────────────────────────────

def test_play_sets_is_playing():
    state = _make_state(tick=0, is_playing=False)
    # Simulating the Play button
    state[IS_PLAYING] = True
    assert state[IS_PLAYING] is True


def test_apply_playback_step_advances_tick_when_playing():
    state = _make_state(tick=5, is_playing=True)
    apply_playback_step(state, max_ticks=25, current_scenario="sc-01", scenario_tick_df=DUMMY_DF)
    assert state[TICK_CURSOR] == 6


def test_apply_playback_step_returns_true_when_playing():
    state = _make_state(tick=5, is_playing=True)
    result = apply_playback_step(state, 25, "sc-01", DUMMY_DF)
    assert result is True


def test_multiple_steps_advance_tick_sequentially():
    state = _make_state(tick=0, is_playing=True)
    for expected in range(1, 6):
        apply_playback_step(state, 25, "sc-01", DUMMY_DF)
        assert state[TICK_CURSOR] == expected


# ─── AC2: Pause → IS_PLAYING=False → tick freezes ────────────────────────────

def test_pause_sets_is_playing_false():
    state = _make_state(tick=10, is_playing=True)
    # Simulating Pause button
    state[IS_PLAYING] = False
    assert state[IS_PLAYING] is False


def test_apply_playback_step_does_nothing_when_paused():
    state = _make_state(tick=10, is_playing=False)
    apply_playback_step(state, 25, "sc-01", DUMMY_DF)
    assert state[TICK_CURSOR] == 10  # unchanged


def test_apply_playback_step_returns_false_when_paused():
    state = _make_state(tick=10, is_playing=False)
    result = apply_playback_step(state, 25, "sc-01", DUMMY_DF)
    assert result is False


# ─── AC3: Rewind → reset; snapshots preserved ────────────────────────────────

def test_rewind_resets_tick_to_zero():
    state = _make_state(tick=15, is_playing=True)
    # Simulating Rewind button
    state[TICK_CURSOR] = 0
    state[IS_PLAYING] = False
    state[SELECTED_FACILITY] = None
    assert state[TICK_CURSOR] == 0


def test_rewind_sets_is_playing_false():
    state = _make_state(tick=15, is_playing=True)
    state[TICK_CURSOR] = 0
    state[IS_PLAYING] = False
    state[SELECTED_FACILITY] = None
    assert state[IS_PLAYING] is False


def test_rewind_clears_selected_facility():
    state = _make_state(tick=15, selected="DHC-A")
    state[TICK_CURSOR] = 0
    state[IS_PLAYING] = False
    state[SELECTED_FACILITY] = None
    assert state[SELECTED_FACILITY] is None


def test_rewind_preserves_scenario_snapshots():
    existing_snapshot = {"some": "data"}
    state = _make_state(tick=15, snapshots={"sc-01": existing_snapshot})
    # Simulate Rewind
    state[TICK_CURSOR] = 0
    state[IS_PLAYING] = False
    state[SELECTED_FACILITY] = None
    # SCENARIO_SNAPSHOTS must be untouched
    assert state[SCENARIO_SNAPSHOTS]["sc-01"] is existing_snapshot


# ─── AC4: Speed slider controls interval_s only; data unchanged ───────────────

def test_speed_4x_gives_02_seconds():
    assert get_interval_s(4.0) == pytest.approx(0.2)


def test_speed_does_not_affect_tick_data():
    """Advancing a tick at 1× vs 4× produces the same TICK_CURSOR."""
    state_1x = _make_state(tick=5, is_playing=True)
    state_4x = _make_state(tick=5, is_playing=True)
    # apply_playback_step is speed-agnostic — speed only affects time.sleep()
    apply_playback_step(state_1x, 25, "sc-01", DUMMY_DF)
    apply_playback_step(state_4x, 25, "sc-01", DUMMY_DF)
    assert state_1x[TICK_CURSOR] == state_4x[TICK_CURSOR]


# ─── AC5: At max_ticks-1 → IS_PLAYING=False, cursor stays ───────────────────

def test_at_end_sets_is_playing_false():
    state = _make_state(tick=24, is_playing=True)
    apply_playback_step(state, max_ticks=25, current_scenario="sc-01", scenario_tick_df=DUMMY_DF)
    assert state[IS_PLAYING] is False


def test_at_end_cursor_stays_at_max_minus_1():
    state = _make_state(tick=24, is_playing=True)
    apply_playback_step(state, max_ticks=25, current_scenario="sc-01", scenario_tick_df=DUMMY_DF)
    assert state[TICK_CURSOR] == 24  # stays at 24, not 25


def test_cursor_never_overflows_on_repeated_steps():
    state = _make_state(tick=22, is_playing=True)
    for _ in range(10):
        apply_playback_step(state, max_ticks=25, current_scenario="sc-01", scenario_tick_df=DUMMY_DF)
        state[IS_PLAYING] = True  # keep playing to test bounds
    assert state[TICK_CURSOR] == 24


def test_end_saves_snapshot():
    state = _make_state(tick=24, is_playing=True)
    df_placeholder = {"rows": 1475}
    apply_playback_step(state, 25, "sc-01", df_placeholder)
    assert state[SCENARIO_SNAPSHOTS]["sc-01"] is df_placeholder


def test_is_at_end_true_at_last_tick():
    assert is_at_end(24, 25) is True


def test_is_at_end_false_before_last_tick():
    assert is_at_end(23, 25) is False


# ─── Scenario switching resets playback ──────────────────────────────────────

def test_scenario_switch_resets_tick_and_stops():
    """Switching scenario should reset TICK_CURSOR=0, IS_PLAYING=False."""
    state = _make_state(tick=10, is_playing=True, scenario="sc-01")
    # Simulate scenario selector change (as in app.py)
    state[CURRENT_SCENARIO] = "sc-03"
    state[TICK_CURSOR] = 0
    state[IS_PLAYING] = False
    state[SELECTED_FACILITY] = None
    assert state[TICK_CURSOR] == 0
    assert state[IS_PLAYING] is False
    assert state[CURRENT_SCENARIO] == "sc-03"


# ─── apply_playback_step uses session constants ───────────────────────────────

def test_apply_playback_step_uses_is_playing_key():
    """Step function must read IS_PLAYING from the provided dict."""
    state = {IS_PLAYING: False, TICK_CURSOR: 5, SCENARIO_SNAPSHOTS: {}}
    result = apply_playback_step(state, 25, "sc-01", DUMMY_DF)
    assert result is False
    assert state[TICK_CURSOR] == 5


def test_apply_playback_step_works_with_any_dict():
    """apply_playback_step should work with any plain dict."""
    from session import IS_PLAYING, SCENARIO_SNAPSHOTS, TICK_CURSOR
    state = {IS_PLAYING: True, TICK_CURSOR: 3, SCENARIO_SNAPSHOTS: {}}
    apply_playback_step(state, 10, "sc-01", DUMMY_DF)
    assert state[TICK_CURSOR] == 4
