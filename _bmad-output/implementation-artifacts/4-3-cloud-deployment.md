---
status: review
baseline_commit: NO_VCS
---

# Story 4.3: Streamlit Cloud Deployment

As the project lead,
I want the app deployable to Streamlit Cloud as a backup demo option,
So that a laptop failure during the June 9-10 presentation does not end the demo.

## Acceptance Criteria

**AC1:** requirements.txt committed (uv export --no-dev); all runtime deps present
**AC2:** data/scenarios/ all 17 files committed; app loads without error on Cloud
**AC3:** DIAGNET_SCREENSHOT_ENABLED=false → st.info("Screenshot disabled in this environment.") — no error
**AC4:** Cloud URL and setup instructions documented in README.md

## Tasks/Subtasks

- [x] T1: Regenerate requirements.txt with --no-dev flag
- [x] T2: Write/update README.md with local + Cloud deployment instructions
- [x] T3: Write tests/test_cloud_compat.py
- [x] T4: Full suite passes

## Dev Notes

- `uv export --format requirements-txt --no-hashes --no-dev` for clean Cloud requirements
- README.md: local setup, regenerate data command, Streamlit Cloud deploy steps, DIAGNET_SCREENSHOT_ENABLED note
- Cloud URL placeholder: https://diagnet-simul.streamlit.app (update after actual deployment)
- Screenshot already disabled by env var (tested in test_export.py) — reference don't retest

## Dev Agent Record
### Implementation Plan
requirements.txt regenerated with `uv export --no-dev --no-hashes` (161 lines, all 11 runtime deps, no dev deps). README.md created with local setup, data generation, testing, and Streamlit Cloud instructions. test_cloud_compat.py covers: requirements correctness, 17-file data presence, README, .streamlit config, screenshot env var, no CDN imports, no generation/ boundary violations.

### Completion Notes
- ✅ requirements.txt: 11 runtime deps present, dev deps excluded, all lines pinned
- ✅ data/scenarios/: all 17 files present, total < 2 MB
- ✅ README.md: Cloud setup + DIAGNET_SCREENSHOT_ENABLED instructions
- ✅ generation/ import boundary enforced across app.py, viz/, tabs/ — verified by tests
- ✅ 22 tests; 342/342 total green
- Cloud URL placeholder in README — update after actual deployment

## File List

- `requirements.txt` (updated — no-dev export, 161 lines)
- `README.md` (created — full setup + Cloud deployment guide)
- `tests/test_cloud_compat.py` (created — 22 tests)

## Change Log

- 2026-06-05: Story 4.3 complete — Cloud deployment readiness; 22 tests; suite 342/342
