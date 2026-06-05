"""Playback loop helpers — pure functions, no Streamlit dependency.

These functions contain the tick-advancement logic used by app.py's
st.rerun() loop. Keeping them here makes the behaviour testable in
isolation and keeps app.py as thin wiring only.
"""
from __future__ import annotations

# Base interval at 1× speed (seconds between st.rerun() calls)
_BASE_INTERVAL_S = 0.8


def get_interval_s(speed_multiplier: float) -> float:
    """Convert playback speed to sleep interval in seconds.

    Formula: interval_s = 0.8 / speed_multiplier

    Speed → interval mapping:
        0.5× → 1.6 s
        1.0× → 0.8 s
        2.0× → 0.4 s
        4.0× → 0.2 s

    Args:
        speed_multiplier: Slider value in range [0.5, 4.0].

    Returns:
        Sleep interval in seconds.
    """
    if speed_multiplier <= 0:
        return _BASE_INTERVAL_S
    return _BASE_INTERVAL_S / speed_multiplier


def advance_tick(current_tick: int, max_ticks: int) -> int:
    """Increment the tick cursor, clamped to [0, max_ticks - 1].

    Args:
        current_tick: Current tick cursor value.
        max_ticks: Total number of ticks in the scenario (exclusive upper bound).

    Returns:
        New tick value — never exceeds max_ticks - 1.
    """
    return min(current_tick + 1, max_ticks - 1)


def is_at_end(current_tick: int, max_ticks: int) -> bool:
    """Return True if the playback cursor has reached the last tick."""
    return current_tick >= max_ticks - 1


def apply_playback_step(
    state: dict,
    max_ticks: int,
    current_scenario: str,
    scenario_tick_df: object,
) -> bool:
    """Apply one tick of the playback loop to the state dict.

    Advances TICK_CURSOR, stops playback at end, saves completed snapshot.
    Returns True if a rerun should be triggered, False if nothing changed.

    This function is pure (mutates only the provided dict) and has no
    Streamlit dependency, making it fully testable in isolation.

    Args:
        state: Session state dict (must contain IS_PLAYING, TICK_CURSOR,
               SCENARIO_SNAPSHOTS keys from session.py constants).
        max_ticks: Total tick count for the active scenario.
        current_scenario: Active scenario id (e.g. "sc-01").
        scenario_tick_df: DataFrame to save in SCENARIO_SNAPSHOTS on completion.

    Returns:
        True if IS_PLAYING was True (caller should trigger st.rerun()).
        False if not playing — no state change.
    """
    from session import IS_PLAYING, SCENARIO_SNAPSHOTS, TICK_CURSOR

    if not state.get(IS_PLAYING, False):
        return False

    new_tick = advance_tick(state[TICK_CURSOR], max_ticks)
    state[TICK_CURSOR] = new_tick

    if is_at_end(new_tick, max_ticks):
        state[IS_PLAYING] = False
        state[SCENARIO_SNAPSHOTS][current_scenario] = scenario_tick_df

    return True
