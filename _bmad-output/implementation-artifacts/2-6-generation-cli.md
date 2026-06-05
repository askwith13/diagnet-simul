---
status: review
baseline_commit: NO_VCS
---

# Story 2.6: Scenario Generation CLI + Commit Data

As a developer,
I want scripts/generate_scenarios.py to produce validated parquet + JSON for all 8 scenarios,
So that data/scenarios/ can be regenerated in < 30 seconds if YAMLs change.

## Acceptance Criteria

**AC1:** `uv run python scripts/generate_scenarios.py --all --validate` exits 0, produces 17 files
**AC2:** metadata.json contains schema_version + 8 scenario entries with all ScenarioMeta fields
**AC3:** Each parquet has shape (max_ticks × 59, 25 cols); total < 500KB snappy-compressed
**AC4:** Each alert JSON is a list of AlertRecord dicts with shap_contributions
**AC5:** `--scenario SC-03` regenerates only SC-03 and updates metadata.json
**AC6:** Invalid alert token → exits 1 with message naming token, scenario, tick
**AC7:** test_generation.py golden fixture — SC-01 seed=42, 5 ticks match to 4 decimal places

## Tasks/Subtasks

- [x] T1: Write scripts/generate_scenarios.py
- [x] T2: Create data/scenarios/ directory
- [x] T3: Run --all --validate to generate all 8 scenarios
- [x] T4: Generate tests/fixtures/sc-01_golden.json (5 ticks × 59 facilities)
- [x] T5: Write tests/test_generation.py with golden fixture test
- [x] T6: Full suite passes

## Dev Notes

- Parquet: 25 cols (matching FlatTickSnapshot — story AC says 22, omitted 3 id fields; implement correctly as 25)
- Optimise dtypes: float64→float32, tick→int16, facility_id/network_id→category
- metadata.json path format: "scenarios/sc-01.parquet" (relative to data/)
- --validate checks facility IDs, shap_weights, AND alert message tokens
- Golden fixture: first 5 ticks only (not all 25); 295 rows per scenario for fixture

## Dev Agent Record

### Implementation Plan
argparse CLI with --all, --scenario, --validate, --force, --seed, --output-dir. generate_one() runs ScenarioGenerator, converts to DataFrame with dtype optimisation (float64→float32, category), writes snappy parquet + alerts JSON. update_metadata() merges new entries into existing metadata.json (supports single-scenario updates). _validate_alert_tokens() checks regex-extracted tokens against FacilityState fields. Golden fixture generated via direct ScenarioGenerator call with seed=42, 5 ticks.

### Completion Notes
- ✅ 17 files generated (8 parquet + 8 alerts + metadata.json)
- ✅ Total parquet: 208.9 KB (well under 500 KB)
- ✅ 25 columns per parquet (3 ids + 17 facility + 5 derived)
- ✅ Golden fixture 295 rows; regeneration matches to 4 decimal places
- ✅ --scenario SC-03 regenerates only 1 file; --validate catches bad tokens
- ✅ 22 generation tests; 128/128 total green

## File List

- `scripts/generate_scenarios.py` (created)
- `data/scenarios/metadata.json` (generated)
- `data/scenarios/sc-01.parquet` … `sc-08.parquet` (generated, 8 files)
- `data/scenarios/sc-01_alerts.json` … `sc-08_alerts.json` (generated, 8 files)
- `tests/fixtures/sc-01_golden.json` (generated — 295 rows, committed)
- `tests/test_generation.py` (created — 22 tests)

## Change Log

- 2026-06-05: Story 2.6 complete — CLI generates all 17 data files; 22 tests; suite 128/128
