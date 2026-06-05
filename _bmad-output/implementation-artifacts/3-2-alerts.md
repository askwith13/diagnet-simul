---
status: review
baseline_commit: NO_VCS
---

# Story 3.2: Alert Card & SHAP Renderer

As a developer,
I want viz/alerts.py with build_alert_cards() and format_shap_bar() as stateless pure functions,
So that every alert has a WCAG AA-compliant format with SHAP explanation.

## Acceptance Criteria

**AC1:** build_alert_cards(alerts, max_cards=14) returns HTML, most-recent-first, at most 14 cards
**AC2:** CRITICAL cards: #dc2626 bg, white text; DTO ADVISORY: #fef3c7/#92400e; BAYESIAN/RECOMMENDATION: #eff6ff/#1e40af
**AC3:** Each card shows: type badge, tick, message text, top-2 SHAP summary
**AC4:** build_alert_cards([]) returns HTML with "No alerts — simulation not started."
**AC5:** format_shap_bar({"patients_queued": 3.24, "tat_hours": 0.84}) returns "↑ Queue load (+3.24) · ↑ TAT (+0.84)"

## Tasks/Subtasks

- [x] T1: Write viz/alerts.py (format_shap_bar, build_alert_cards)
- [x] T2: Write tests/test_alerts.py
- [x] T3: Full suite passes

## Dev Notes

- FIELD_LABELS: patients_queued→"Queue load", tat_hours→"TAT", cascade_dropout_risk→"Cascade risk", etc.
- format_shap_bar: top_n by |val|, ↑ positive / ↓ negative, format (+val) or (-val) to 2dp
- build_alert_cards: ordered by tick descending (most-recent-first); same-tick deduplication by (type+facility_id)
- No session_state, no generation/ imports
- HTML uses inline styles only (Streamlit compatibility)

## Dev Agent Record
### Implementation Plan
format_shap_bar sorts by |val| descending, takes top_n, formats each as "↑/↓ Label (+/-val)". build_alert_cards deduplicates (tick+type+facility) before sorting, then truncates to max_cards. All HTML inline-styled. _CARD_STYLES dict maps alert_type to WCAG AA colour pairs. _FIELD_LABELS maps FacilityState field names to readable labels.

### Completion Notes
- ✅ format_shap_bar worked example matches exactly: "↑ Queue load (+3.24) · ↑ TAT (+0.84)"
- ✅ All 3 WCAG AA colour pairs verified
- ✅ Deduplication, max_cards, most-recent-first ordering all tested
- ✅ 25 tests; 176/176 total green

## File List

- `viz/alerts.py` (created — format_shap_bar, build_alert_cards)
- `tests/test_alerts.py` (created — 25 tests)

## Change Log

- 2026-06-05: Story 3.2 complete — viz/alerts.py; 25 tests; suite 176/176
