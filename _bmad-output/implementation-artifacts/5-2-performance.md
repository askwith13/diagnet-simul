---
status: review
baseline_commit: NO_VCS
---

# Story 5.2: Performance Validation

As a developer,
I want the tick playback and data load NFRs verified with actual measurements,
So that the team knows before the demo whether any optimisation is needed.

## Acceptance Criteria

**AC1:** load_scenario_payloads() completes in < 500ms (all 8 scenarios)
**AC2:** Core per-tick work (DataFrame lookup + figure build for NET-A) < 400ms median over 20 ticks
**AC3:** JSON serialisation of full tick history < 500ms (already verified in test_export.py)

## Tasks/Subtasks

- [x] T1: Write tests/test_performance.py
- [x] T2: Run full suite and verify all performance tests pass
- [x] T3: Confirm AC3 reference — test_export.py::test_json_serialisation_benchmark

## Dev Notes

- AC1: time load_scenario_payloads() — must be < 500ms
- AC2: time DataFrame tick lookup + build_network_figure (NET-A) across 20 ticks — median < 400ms
- Streamlit DOM rendering overhead not measurable in unit tests; core computation measured instead
- AC3 already tested in Story 4.2 — reference, don't retest
- 5 mini-maps for Tab 2 also timed (NFR3: simultaneous rendering)

## Dev Agent Record
### Implementation Plan
9 performance tests across 3 NFR categories. test_performance_summary prints measured values. All thresholds set at NFR limit with observed values well within budget. test_json_serialisation_nfr_reference confirms the cross-reference to test_export.py is intact.

### Completion Notes

Measured on this machine (Linux x86_64, Python 3.12.3):

| NFR | Measured | Limit | Margin |
|---|---|---|---|
| Startup (8 scenarios) | 62.4ms | 500ms | 8.0× headroom |
| Per-tick core (Tab 1) | 29.7ms | 400ms | 13.5× headroom |
| Tab 2 (5 mini-maps) | 80.1ms | 200ms | 2.5× headroom |

- ✅ 9 performance tests; 370/370 total green
- Demo hardware will be faster than this VM; all NFRs met with large margins

## File List

- `tests/test_performance.py` (created — 9 tests)

## Change Log

- 2026-06-05: Story 5.2 complete — all NFRs measured and verified; 9 tests; suite 370/370
