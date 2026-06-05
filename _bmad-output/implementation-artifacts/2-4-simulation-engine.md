---
status: review
baseline_commit: NO_VCS
---

# Story 2.4: Simulation Engine with AI Stubs

As a developer,
I want generation/engine.py to implement ScenarioGenerator with all 5 AI model stubs,
So that pre-computed outputs faithfully represent DiagNet's full capability stack.

## Acceptance Criteria

**AC1:** `.run()` returns max_ticks × facility_count FlatTickSnapshot dicts, all fields populated (no None)
**AC2:** `tick()` returns a new GlobalGenState (s0 is not s1, deep copy confirmed)
**AC3:** DHC-A patients_queued at tick 4 ≈ baseline + 4×1.8 (±5% stochastic noise)
**AC4:** `apply_overflow()` adds overflow_pending to target network hub's patients_queued
**AC5:** B1 output ∈ [0.20, 0.95] for any valid facility state
**AC6:** M2 betweenness_centrality ∈ [0.0, 1.0]; composite_bottleneck_score = 0.6×norm_b + 0.4×norm_p
**AC7:** M4 returns routes sorted by estimated_tat ascending

## Tasks/Subtasks

- [x] T1: Internal state dataclasses (NetworkGenState, GlobalGenState)
- [x] T2: Graph builder (build_network_graph from networks.yaml links)
- [x] T3: AI model stubs as pure module-level functions (b1, m1, m2, m4)
- [x] T4: ScenarioGenerator._init_global_state(), _tick(), apply_overflow(), run()
- [x] T5: Snapshot serialisation to FlatTickSnapshot dicts
- [x] T6: Write tests/test_engine.py
- [x] T7: Full suite passes

## Dev Notes

- GlobalGenState is generation-only; never imported by Streamlit app
- deep copy each tick to satisfy immutability contract
- Integer fields (machines, modules, chw_available): use round() when applying float deltas, floor at 0
- Rate fields (smear_positivity_rate etc): clamp [0.0, 1.0]
- SHAP computation inline here; Story 2.5 extracts to shap_calculator.py
- B1 uses logistic curve on days_remaining = stock/daily_consumption vs 7-day half-life
- M2 normalises betweenness/pagerank before computing bottleneck_score
- Status computed each tick from global thresholds (not per-facility custom thresholds)

## Dev Agent Record

### Implementation Plan
NetworkGenState + GlobalGenState as generation-only dataclasses. ScenarioGenerator caches baselines, graphs, facility→network lookup, and overflow routes at init. _tick() deep-copies state before mutations (immutability contract). B1 uses logistic curve on days_remaining vs 7-day half-life. M2 normalises betweenness/pagerank per-network before computing bottleneck_score. M4 Dijkstra sorts by (travel_min/60 + dest_tat_hours). apply_overflow() is static method to enable direct testing. SHAP inline pending Story 2.5 extraction. test import issue: apply_overflow is static method not module function — fixed test import.

### Completion Notes
- ✅ All 7 ACs satisfied
- ✅ 28 engine tests; 93/93 total green
- ✅ run() returns 25×59=1475 rows for SC-01
- ✅ tick() identity check passes
- ✅ overflow adds to hub patients_queued and clears pending
- ✅ SC-08 initial_states override baselines correctly

## File List

- `generation/engine.py` (created — ~330 lines)
- `tests/test_engine.py` (created — 28 tests)

## Change Log

- 2026-06-05: Story 2.4 complete — simulation engine with all 5 AI stubs; 28 tests green; suite 93/93
