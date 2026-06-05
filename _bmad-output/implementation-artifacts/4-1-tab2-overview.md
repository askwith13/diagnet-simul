---
status: review
baseline_commit: NO_VCS
---

# Story 4.1: Tab 2 — Multi-Hub Overview

As a Programme Manager,
I want to see all 5 networks simultaneously with bottleneck heatmap and global alerts,
So that I can identify system-wide cascade risk in a single view.

## Acceptance Criteria

**AC1:** 5 mini-maps rendered simultaneously; colour-encoding consistent with Tab 1
**AC2:** System-wide bottleneck heatmap (bar chart) shows composite_bottleneck_score for all 59 nodes
**AC3:** Global alert feed — combined stream from all networks with network ID badge
**AC4:** "Run SC-08" button sets CURRENT_SCENARIO="sc-08", TICK_CURSOR=0, IS_PLAYING=True
**AC5:** Inter-network flow diagram shows 3 connections; red when critical cascade active

## Tasks/Subtasks

- [x] T1: Implement tabs/overview.py — build_bottleneck_heatmap, build_inter_network_figure, get_global_alerts, render_overview_tab
- [x] T2: Write tests/test_overview.py covering pure helpers
- [x] T3: Full suite passes

## Dev Notes

- build_bottleneck_heatmap(tick_df) → go.Figure: horizontal bar, all 59 nodes, sorted desc by bottleneck_score
- build_inter_network_figure(inter_network_links, network_alert_counts) → go.Figure: 5 network nodes + 3 edges coloured by flow status
- Inter-network links from graph_cache or loaded fresh (networks.yaml inter_network_links)
- get_global_alerts(alerts, up_to_tick) → all alerts sorted by tick desc (no per-network filter)
- "Run SC-08" button: mutates session_state and calls st.rerun()

## Dev Agent Record
### Implementation Plan
tabs/overview.py: 4 pure helpers + render_overview_tab. build_bottleneck_heatmap sorts by score ascending (for horizontal bar bottom-to-top presentation). build_inter_network_figure uses static _NET_POSITIONS + _INTER_LINKS; edges coloured red if either endpoint network is critical. compute_network_critical filters tick_df by status. "Run SC-08" button mutates session_state and reruns. Global alert feed annotates messages with [NET-X] badges.

### Completion Notes
- ✅ All 5 ACs satisfied
- ✅ 59 bars in heatmap, sorted ascending
- ✅ 5-node + 3-edge inter-network diagram; critical = red
- ✅ "Run SC-08" state mutation tested
- ✅ 22 tests; 303/303 total green

## File List

- `tabs/overview.py` (implemented)
- `tests/test_overview.py` (created — 22 tests)

## Change Log

- 2026-06-05: Story 4.1 complete — Tab 2 Multi-Hub Overview; 22 tests; suite 303/303
