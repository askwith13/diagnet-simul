---
status: review
baseline_commit: NO_VCS
---

# Story 3.1: Network Map Figure Builder

As a developer,
I want viz/network_map.py with build_network_figure() and build_mini_map() as stateless pure functions,
So that Tab 1 and Tab 2 can render accurate network maps without any simulation logic.

## Acceptance Criteria

**AC1:** build_network_figure() returns go.Figure with node size encoding (hub=30, truenat=22, microscopy=16, chc=12) and colour encoding (ok/#22c55e, warning/#f59e0b, critical/#ef4444, offline/grey)
**AC2:** Critical nodes have a second scatter trace (static outer ring, 1.5× size, 0.4 opacity)
**AC3:** Active reroute edges rendered as blue dashed lines; healthy=green solid; at-risk=amber; critical=red dashed
**AC4:** Empty DataFrame → go.Figure() without raising
**AC5:** build_mini_map() returns go.Figure at ~200×200px with colour-only encoding (no tooltips)

## Tasks/Subtasks

- [x] T1: Add FacilityLayout TypedDict to core/models.py + load_network_layout() to core/network_layout.py
- [x] T2: Create viz/__init__.py and viz/network_map.py
- [x] T3: Write tests/test_network_map.py
- [x] T4: Full suite passes

## Dev Notes

- viz/ functions are pure: (tick_df, tick, network_id, layout, links, ...) → go.Figure
- layout: Dict[facility_id, FacilityLayout] — from networks.yaml via load_network_layout()
- links: List[[src, dst, travel_time]] — for edge drawing
- Edge groups: green-solid (both ok), amber-solid (one warning), red-dashed (one critical), blue-dashed (reroute)
- critical outer ring: separate go.Scatter trace, marker size = 1.5× node size, opacity 0.4
- Hover template shows: display_name, status, key metrics (patients_queued, cartridges, tat_hours, etc.)
- Never import from generation/

## Dev Agent Record

### Implementation Plan
FacilityLayout TypedDict added to core/models.py. core/network_layout.py provides load_network_layout(), load_all_layouts(), load_network_links() — safe for runtime import. viz/network_map.py: pure functions, no session_state. Reroutes drawn as separate traces BEFORE topology edges (reroutes may not exist in topology — bug found and fixed during test). Critical outer ring as markers-only scatter trace at 1.5× size. Edge grouping: reroute first, then ok/warning/critical buckets.

### Completion Notes
- ✅ All 5 ACs satisfied
- ✅ Reroute fix: draw independently from topology links
- ✅ 23 viz tests + 151/151 total green

## File List

- `core/models.py` (updated — added FacilityLayout TypedDict)
- `core/network_layout.py` (created — layout helpers)
- `viz/__init__.py` (created)
- `viz/network_map.py` (created — build_network_figure, build_mini_map)
- `tests/test_network_map.py` (created — 23 tests)

## Change Log

- 2026-06-05: Story 3.1 complete — viz/network_map.py; 23 tests; suite 151/151
