"""Session state key constants and initialisation.

All session_state keys are defined here as module-level constants.
No module in the app may use raw string keys — always import from here.

No Streamlit import: init_session_state() accepts any dict-like object,
making it testable without a running Streamlit server.
"""
from __future__ import annotations

from typing import Any

# ─── Key constants ────────────────────────────────────────────────────────────
# Values equal their snake_case names (makes debugging transparent).

SCENARIO_DATA      = "scenario_data"       # Dict[str, ScenarioPayload] — all 8 loaded at startup
CURRENT_SCENARIO   = "current_scenario"    # str — active scenario id (e.g. "sc-01")
TICK_CURSOR        = "tick_cursor"         # int — current playback position
IS_PLAYING         = "is_playing"          # bool — playback running
SELECTED_FACILITY  = "selected_facility"   # Optional[str] — set by plotly_click
SCENARIO_SNAPSHOTS = "scenario_snapshots"  # Dict[str, Any] — completed run histories for Tab 4
GRAPH_CACHE        = "graph_cache"         # Dict[str, Any] — network layout positions
PERF_LOG           = "perf_log"            # List[float] — tick render times (debug mode)


# ─── Initialisation ───────────────────────────────────────────────────────────

def init_session_state(
    scenario_data: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Initialise all session state keys with correct defaults.

    Args:
        scenario_data: Dict mapping scenario_id to ScenarioPayload (all 8).
        state: Dict-like to write into. If None, a plain dict is created and
               returned. Pass ``st.session_state`` in app.py.

    Returns:
        The ``state`` object with all keys initialised. Keys that already
        exist are preserved (idempotent on subsequent calls).
    """
    if state is None:
        state = {}

    defaults: dict[str, Any] = {
        SCENARIO_DATA:      scenario_data,
        CURRENT_SCENARIO:   next(iter(scenario_data), ""),
        TICK_CURSOR:        0,
        IS_PLAYING:         False,
        SELECTED_FACILITY:  None,
        SCENARIO_SNAPSHOTS: {},
        GRAPH_CACHE:        {},
        PERF_LOG:           [],
    }

    for key, default in defaults.items():
        if key not in state:
            state[key] = default

    return state
