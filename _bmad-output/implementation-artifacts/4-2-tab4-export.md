---
status: review
baseline_commit: NO_VCS
---

# Story 4.2: Tab 4 — Scenario Comparison & Export

As an IT/Data team member,
I want to compare two completed scenarios and export the network map as a PNG,
So that I can demonstrate DiagNet's data feasibility and produce slide assets.

## Acceptance Criteria

**AC1:** SC-A vs SC-B + metric dropdown → dual-line Plotly chart, distinctly coloured, labelled with display_names
**AC2:** "Download config" → browser downloads networks.yaml
**AC3:** Screenshot button with DIAGNET_SCREENSHOT_ENABLED=true → plotly.io.write_image, 1920×1080, st.success
**AC4:** DIAGNET_SCREENSHOT_ENABLED=false → st.info("Screenshot disabled in this environment.")

## Tasks/Subtasks

- [x] T1: Implement tabs/export.py — build_comparison_figure, is_screenshot_enabled, render_export_tab
- [x] T2: Write tests/test_export.py
- [x] T3: Full suite passes

## Dev Notes

- build_comparison_figure(df_a, df_b, metric, label_a, label_b) → dual-line figure aggregating metric by tick
- Aggregation: sum for stock/count fields, mean for rate/risk fields
- is_screenshot_enabled() → os.environ.get("DIAGNET_SCREENSHOT_ENABLED","true").lower() != "false"
- Screenshot: takes fig from session or builds fresh from current state; saves to diagnet_screenshot.png
- Config viewer: st.code(networks_yaml), st.download_button for networks.yaml bytes

## Dev Agent Record
### Implementation Plan
build_comparison_figure: groupby tick + agg (sum for stocks, mean for rates) → dual-line figure. is_screenshot_enabled: env var check. take_screenshot: plotly.io.write_image with kaleido. render_export_tab: gated comparison (needs ≥2 snapshots), YAML config viewer + download, screenshot with env var gate. JSON serialisation benchmark included in test_export.py — both SC-01 (< 500ms) and all 8 scenarios combined (< 500ms) pass.

### Completion Notes
- ✅ All 4 ACs satisfied
- ✅ NFR8 verified: SC-01 serialisation and all-8 combined both < 500ms
- ✅ DIAGNET_SCREENSHOT_ENABLED env var correctly gates screenshot
- ✅ Comparison chart: 2 traces, distinct colours, scenario display_names as labels
- ✅ 17 tests; 320/320 total green

## File List

- `tabs/export.py` (implemented)
- `tests/test_export.py` (created — 17 tests including NFR8 benchmark)

## Change Log

- 2026-06-05: Story 4.2 complete — Tab 4 Export; NFR8 verified; 17 tests; suite 320/320
