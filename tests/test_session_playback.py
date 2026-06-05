"""Tests for session.py and playback.py."""
import pytest

import session as sess
from playback import advance_tick, get_interval_s, is_at_end
from session import (
    CURRENT_SCENARIO,
    GRAPH_CACHE,
    IS_PLAYING,
    PERF_LOG,
    SCENARIO_DATA,
    SCENARIO_SNAPSHOTS,
    SELECTED_FACILITY,
    TICK_CURSOR,
    init_session_state,
)


# ─── Key constants ────────────────────────────────────────────────────────────

def test_all_8_constants_defined():
    expected = {
        "SCENARIO_DATA", "CURRENT_SCENARIO", "TICK_CURSOR", "IS_PLAYING",
        "SELECTED_FACILITY", "SCENARIO_SNAPSHOTS", "GRAPH_CACHE", "PERF_LOG",
    }
    for name in expected:
        assert hasattr(sess, name), f"session.py missing constant {name}"


def test_constants_equal_snake_case_names():
    assert SCENARIO_DATA      == "scenario_data"
    assert CURRENT_SCENARIO   == "current_scenario"
    assert TICK_CURSOR        == "tick_cursor"
    assert IS_PLAYING         == "is_playing"
    assert SELECTED_FACILITY  == "selected_facility"
    assert SCENARIO_SNAPSHOTS == "scenario_snapshots"
    assert GRAPH_CACHE        == "graph_cache"
    assert PERF_LOG           == "perf_log"


# ─── init_session_state ───────────────────────────────────────────────────────

@pytest.fixture
def dummy_scenario_data() -> dict:
    return {"sc-01": {"metadata": {"tick_count": 25}}}


def test_init_session_state_returns_dict(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert isinstance(state, dict)


def test_init_session_state_tick_cursor_zero(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[TICK_CURSOR] == 0


def test_init_session_state_is_playing_false(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[IS_PLAYING] is False


def test_init_session_state_selected_facility_none(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[SELECTED_FACILITY] is None


def test_init_session_state_scenario_data_stored(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[SCENARIO_DATA] is dummy_scenario_data


def test_init_session_state_snapshots_empty_dict(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[SCENARIO_SNAPSHOTS] == {}


def test_init_session_state_perf_log_empty_list(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[PERF_LOG] == []


def test_init_session_state_graph_cache_empty_dict(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[GRAPH_CACHE] == {}


def test_init_session_state_current_scenario_first_key(dummy_scenario_data):
    state = init_session_state(dummy_scenario_data)
    assert state[CURRENT_SCENARIO] == "sc-01"


def test_init_session_state_writes_into_provided_dict(dummy_scenario_data):
    existing = {}
    result = init_session_state(dummy_scenario_data, state=existing)
    assert result is existing
    assert existing[TICK_CURSOR] == 0


def test_init_session_state_idempotent(dummy_scenario_data):
    """Calling twice preserves existing values."""
    state = init_session_state(dummy_scenario_data)
    state[TICK_CURSOR] = 12
    state[IS_PLAYING] = True
    # Second call should NOT overwrite existing keys
    init_session_state(dummy_scenario_data, state=state)
    assert state[TICK_CURSOR] == 12
    assert state[IS_PLAYING] is True


def test_init_session_state_empty_scenario_data():
    state = init_session_state({})
    assert state[CURRENT_SCENARIO] == ""


# ─── get_interval_s ───────────────────────────────────────────────────────────

def test_get_interval_s_half_speed():
    assert get_interval_s(0.5) == pytest.approx(1.6)


def test_get_interval_s_1x():
    assert get_interval_s(1.0) == pytest.approx(0.8)


def test_get_interval_s_2x():
    assert get_interval_s(2.0) == pytest.approx(0.4)


def test_get_interval_s_4x():
    assert get_interval_s(4.0) == pytest.approx(0.2)


def test_get_interval_s_formula():
    for speed in [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]:
        assert get_interval_s(speed) == pytest.approx(0.8 / speed)


def test_get_interval_s_zero_returns_base():
    assert get_interval_s(0) == pytest.approx(0.8)


# ─── advance_tick ─────────────────────────────────────────────────────────────

def test_advance_tick_normal():
    assert advance_tick(10, 35) == 11


def test_advance_tick_at_boundary():
    """At max_ticks - 1, stays there (does not overflow)."""
    assert advance_tick(34, 35) == 34


def test_advance_tick_one_before_end():
    assert advance_tick(33, 35) == 34


def test_advance_tick_zero():
    assert advance_tick(0, 25) == 1


def test_advance_tick_never_exceeds_max_minus_1():
    for tick in range(30, 36):
        result = advance_tick(tick, 35)
        assert result <= 34, f"advance_tick({tick}, 35) = {result}, expected ≤ 34"


def test_advance_tick_max_ticks_1():
    """Edge case: single-tick scenario."""
    assert advance_tick(0, 1) == 0


# ─── is_at_end ────────────────────────────────────────────────────────────────

def test_is_at_end_false_mid_scenario():
    assert is_at_end(10, 25) is False


def test_is_at_end_true_at_last_tick():
    assert is_at_end(24, 25) is True


def test_is_at_end_true_beyond_end():
    assert is_at_end(30, 25) is True


def test_is_at_end_false_at_zero():
    assert is_at_end(0, 25) is False
