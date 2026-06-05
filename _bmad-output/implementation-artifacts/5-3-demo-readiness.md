---
status: review
baseline_commit: NO_VCS
---

# Story 5.3: WCAG AA Audit, Offline Test & Demo Rehearsal

As the project lead,
I want colour contrast, offline compatibility, and demo success criteria all verified,
So that the team enters June 9-10 with confidence.

## Acceptance Criteria

**AC1:** All 8 scenarios have ≥1 alert with non-empty SHAP contributions (SC2 demo criterion)
**AC2:** WCAG AA contrast ratios verified programmatically for all 3 alert card colour pairs
**AC3:** No CDN/external URL dependencies in any runtime module
**AC4:** Visual QA tick checkpoints specified (ticks 0, 7, 15, 25, 30, 35) across all scenarios

## Tasks/Subtasks

- [x] T1: Write tests/test_demo_readiness.py — WCAG, demo criteria, offline checks
- [x] T2: Full suite passes with all 3 demo success criteria verified
- [x] T3: Update MEMORY.md to record project completion state

## Dev Notes

- WCAG relative luminance formula; contrast_ratio = (L_lighter + 0.05) / (L_darker + 0.05) ≥ 4.5 for AA
- Demo SC1 (no traceback) verified via pre-computed data integrity (all 8 parquets complete)
- Demo SC2 (≥1 SHAP per scenario) verified via alerts JSON shap_contributions
- Demo SC3 (Tab 2 no lag) already verified in test_performance.py (80ms)
- Offline: no HTTP imports, no external URLs, bundled data

## Dev Agent Record
### Implementation Plan
Implemented _relative_luminance() and _contrast_ratio() using WCAG 2.1 formula. CDN scanner initially caught pattern strings in test file itself — fixed by scanning runtime modules only. Demo rehearsal checklist prints pass/fail for all 6 criteria and asserts all_pass.

### WCAG AA Contrast Results
- CRITICAL (#dc2626 / #ffffff): **4.83:1** ✅ (≥4.5 required)
- DTO ADVISORY (#fef3c7 / #92400e): **6.37:1** ✅
- BAYESIAN (#eff6ff / #1e40af): **8.01:1** ✅

### Completion Notes
- ✅ AC1: All 8 scenarios with SHAP on ≥1 alert verified
- ✅ AC2: All 3 colour pairs pass WCAG AA — ratios 4.83, 6.37, 8.01
- ✅ AC3: No CDN imports in runtime modules
- ✅ AC4: Visual QA tick checkpoints (0, 7, 15, 25, 30, 35) all have 59-row data
- ✅ Demo checklist: **READY FOR DEMO** (all 6 criteria green)
- ✅ 16 tests; 386/386 total green

## File List

- `tests/test_demo_readiness.py` (created — 16 tests)

## Change Log

- 2026-06-05: Story 5.3 complete — demo readiness verified; 16 tests; suite 386/386
