---
status: review
baseline_commit: NO_VCS
---

# Story 2.1: networks.yaml — All 59 Facilities

As a domain expert,
I want all 5 networks with facilities, baselines, thresholds, and links defined in a validated YAML,
So that facility parameters can be adjusted without touching Python code.

## Acceptance Criteria

**AC1:** 5 networks (NET-A–NET-E), correct counts: A=14, B=11, C=13, D=9, E=12 (total 59)
**AC2:** Every facility has: display_name, type, x/y, baseline (all FacilityState fields), thresholds
**AC3:** Intra-network links as [from, to, travel_time_min] triples
**AC4:** Top-level inter_network_links with 3 connections (NET-A↔NET-C, NET-B↔NET-D, NET-D→NET-A)
**AC5:** `python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('config/networks.yaml').read_text())"` exits 0

## Tasks/Subtasks

- [x] T1: Create config/ directory and networks.yaml (59 facilities)
- [x] T2: Write tests/test_networks_yaml.py
- [x] T3: Run full test suite — smoke + models pass; contract tests still red

## Dev Notes

- Facility counts: NET-A=14 (1 hub+3 TL+4 MC+6 CHC), NET-B=11 (1+2+3+5), NET-C=13 (1+2+4+6), NET-D=9 (1+1+2+5), NET-E=12 (1+2+3+6)
- Hub naming: DHC-A, TH-B, DHC-C, DHC-D, DHC-E (DHC-D required by architecture inter_network_links)
- All 17 FacilityState baseline fields required per facility (zero where not applicable)
- Pydantic schema validation deferred to Story 2.3

## Dev Agent Record

### Implementation Plan
59 facilities across 5 networks following PRD §4 facility counts and profiles. Baselines calibrated by facility type (hub: high-volume; CHC: low-volume, high dropout risk). NET-D has highest travel times (95–130 min to hub) reflecting tribal/remote profile. All 17 FacilityState fields present per facility. 3 inter-network links matching architecture.md schema.

### Completion Notes
- ✅ 5 networks, 59 facilities (A=14, B=11, C=13, D=9, E=12)
- ✅ All 17 FacilityState fields in every baseline (including daily_consumption)
- ✅ 3 inter-network links with correct flow_types (culture_dst, overflow, overflow)
- ✅ DHC-D is NET-D hub (required by architecture for overflow scenarios)
- ✅ 16 YAML tests + 39 total tests green; contract tests still red

## File List

- `config/networks.yaml` (created — 59 facilities, ~680 lines)
- `tests/test_networks_yaml.py` (created — 16 tests)

## Change Log

- 2026-06-05: Story 2.1 complete — networks.yaml with all 59 facilities; 16 tests green; suite 39/39
