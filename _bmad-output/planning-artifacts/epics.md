---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-06-05'
inputDocuments:
  - "_bmad-output/planning-artifacts/Simulation PRD.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# DiagNet_Simul - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for DiagNet_Simul, decomposing requirements from the PRD v1.1 and Architecture document into implementable stories for the 5-day sprint (June 4–9, 2026).

## Requirements Inventory

### Functional Requirements

FR1: System loads 5 pre-configured networks (NET-A through NET-E) from config/networks.yaml at startup
FR2: System models 59 nodes across 5 networks (5 hubs, 13 Truenat labs, 17 microscopy centres, 24 CHCs) with per-tier visual encoding
FR3: System models 3 inter-network connections (NET-A↔NET-C, NET-B↔NET-D, NET-D→NET-A) with YAML-defined schema
FR4: Each facility carries 17 FacilityState fields with warn/critical thresholds defined per-facility in YAML
FR5: System computes 5 derived metrics per tick: network_betweenness_score, pagerank_score, composite_bottleneck_score, effective_capacity_days, predicted_stockout_day
FR6: GlobalState coordinates all 5 NetworkStates with synchronous global tick and inter-network overflow via apply_overflow()
FR7: System pre-computes 8 scenarios from YAML config (SC-01 through SC-08) via offline generation pipeline
FR8: Each scenario stores scripted alert sequences at specified ticks (type, recipient, message, SHAP contributions, severity)
FR9: Scenario YAML supports per_tick_deltas, shap_weights, reroutes, alerts with str.format_map() interpolation, recommended_actions
FR10: SC-08 starts from pre-loaded post-crisis YAML baselines (not derived from prior run); defines impact metrics
FR11: B1 stub computes P(stockout in 14 days) per facility using scipy.stats.nbinom; output range [0.20, 0.95]
FR12: B2 stub produces failure mode probabilities via lookup table; output range [0.10, 0.90]
FR13: M1 stub produces anomaly score [0.30, 0.95] using Z-score on composite index; threshold 0.75
FR14: M2 computes betweenness centrality, PageRank, and composite_bottleneck_score (0.6×betweenness + 0.4×PageRank) using NetworkX
FR15: M4 computes optimal referral route via Dijkstra + pre-loaded Q-table YAML lookup; no M3 dependency
FR16: SHAP approximation: shap_f = per_tick_delta × shap_weight; computed at generation time; stored in alert JSON
FR17: Every alert card displays top-2 SHAP contributors (±bar); Tab 3 SHAP waterfall shows top-5 (labelled "Approximate · simulation mode")
FR18: Persistent top bar: Network selector, Scenario selector, Play/Pause/Rewind, Playback Speed slider (0.5×–4×), tick counter, global alert badge
FR19: Tab 1 Network Map: Plotly network graph with node encoding (size=tier, colour=status, static outer ring for critical nodes), edge encoding (green/amber/red solid, blue dashed reroute), alert panel, metrics bar
FR20: Alert panel: 14 most recent AlertRecords for selected network; persists for scenario lifetime; same-tick deduplication; tick-0 placeholder text
FR21: Tab 2 Multi-Hub Overview: 5-column mini-maps, inter-network flow arrows, system-wide heatmap (bottleneck scores), global alert feed, "Run SC-08" button
FR22: Tab 3 Facility Detail: plotly_click sets session_state.selected_facility; 4 time-series charts (patients queued, cartridges, TAT, cascade dropout risk) with threshold lines; SHAP waterfall; recommended actions (3 YAML strings); alert history
FR23: Tab 4 Analytics & Export: scenario comparison via two dropdowns (post-hoc, dual-line Plotly chart); config viewer (read-only + download button)
FR24: Screenshot: exports active Plotly network map figure as PNG 1920×1080 via plotly.io.write_image() with kaleido; simulation paused before capture
FR25: Demo success criteria: all 8 scenarios complete without traceback; SHAP panel visible on ≥1 alert per scenario; Tab 2 renders 5 networks without perceptible lag
FR26: Speed slider controls playback animation rate only (sleep_interval_s); per-tick delta magnitudes invariant to speed
FR27: Reset/Rewind preserves completed scenario tick history in scenario_snapshots[scenario_id]; clears selected_facility; halts is_playing before state clear
FR28: App startup validates all 8 parquet paths from metadata.json; hard fails with st.error() + st.stop() if any missing
FR29: Streamlit Cloud deployment with DIAGNET_SCREENSHOT_ENABLED env var to disable kaleido on Cloud

### NonFunctional Requirements

NFR1: Tick playback latency < 400ms at 4× speed (cursor increment + st.rerun() only — no simulation math at runtime)
NFR2: Full pre-computed data load at startup < 500ms (< 500KB total across 8 scenarios)
NFR3: All 5 networks renderable on Tab 2 simultaneously without perceptible lag (renders from pre-computed parquet)
NFR4: Same scenario always plays identically (pre-computed outputs are deterministic by definition)
NFR5: App runs fully offline; kaleido bundled; no CDN dependencies; all assets local
NFR6: Alert card WCAG AA colour pairs: CRITICAL=#dc2626/white (4.5:1); DTO ADVISORY=#fef3c7/#92400e (7.3:1); BAYESIAN=#eff6ff/#1e40af (5.9:1)
NFR7: Compatible with Chrome ≥120, Firefox ≥121, Safari ≥17
NFR8: JSON serialisation < 500ms for full tick history; enforced by flat dict format (no nested NetworkState objects)
NFR9: Invalid YAML raises readable Pydantic error (not Python traceback) during generation --validate
NFR10: 80% test line coverage on core/ and generation/ modules (pytest-cov)
NFR11: Golden fixture regression for all 8 scenarios (5-tick golden JSON; asserted on every test run)

### Additional Requirements

- AR1: Two-layer architecture enforced: generation/ (build-time) never imported by app.py, viz/, tabs/, session.py, or playback.py
- AR2: FlatTickSnapshot TypedDict in core/models.py is the sole data contract; parquet column names must match field names exactly
- AR3: uv package manager; all deps via `uv add`; uv.lock committed; requirements.txt exported for Streamlit Cloud
- AR4: Data files committed to repo: data/scenarios/*.parquet, data/scenarios/*_alerts.json, data/scenarios/metadata.json
- AR5: All 8 scenario parquets loaded eagerly at app startup into st.session_state[SCENARIO_DATA]
- AR6: Playback loop: st.rerun() + time.sleep(interval_s); speed→interval: 0.5×=1.6s, 1×=0.8s, 2×=0.4s, 4×=0.2s
- AR7: session_state keys defined as constants in session.py; raw string keys forbidden elsewhere
- AR8: viz/ functions are pure (no session_state reads/writes); always return go.Figure; handle empty DataFrame with empty figure
- AR9: Contract test (tests/test_config_contract.py) must be written before any YAML exists and must be in failing (red) state initially
- AR10: safe_format() helper in core/models.py handles alert message interpolation; missing keys render as [key_name]
- AR11: Module build order: core/models.py → contract tests → YAML configs → generation/engine.py → data generation → viz/ → tabs/ → app.py
- AR12: ScenarioPayload TypedDict wraps tick_df (pd.DataFrame), alerts (List[AlertRecord]), metadata (ScenarioMeta)
- AR13: .streamlit/config.toml sets server.headless=true and browser.gatherUsageStats=false

### UX Design Requirements

N/A — no UX design document. Dashboard specification is fully defined in PRD §8.

### FR Coverage Map

| FR/NFR/AR | Epic | Notes |
|-----------|------|-------|
| AR1–AR13 | Epic 1 | Project scaffold, data contracts, module boundary rules |
| FR1–FR6 | Epic 2 | Network topology, facility data model, derived metrics |
| FR7–FR16 | Epic 2 | Scenarios, AI stubs (B1–M4), SHAP algorithm |
| NFR4, NFR9, NFR11 | Epic 2 | Determinism, config validation, golden fixtures |
| FR17–FR22, FR26–FR28 | Epic 3 | Alert display, top bar, Tab 1, Tab 3, playback semantics |
| NFR1, NFR2 | Epic 3 | Tick latency < 400ms, startup load < 500ms |
| FR21, FR23–FR25, FR29 | Epic 4 | Tab 2, Tab 4, screenshot, Cloud deployment |
| NFR3 | Epic 4 | 5 networks on Tab 2 without lag |
| NFR1–NFR11, FR25 | Epic 5 | All NFRs verified; demo success criteria confirmed |

## Epic List

### Epic 1: Project Foundation
Any developer can clone, install, and have a contract test suite that defines what the system must produce — before YAML or scenarios exist.
**FRs covered:** AR1–AR13

### Epic 2: Scenario Data — All 8 Scenarios Pre-Computed
The presenter has all 8 playable scenarios committed to the repo. Any scenario selected from the dropdown has data ready to display.
**FRs covered:** FR1–FR16, NFR4, NFR9, NFR11

### Epic 3: Primary Demo View (Network Map + Facility Detail)
The DTO and Lab Supervisor can watch the core demo — network map updating tick-by-tick with alerts and SHAP explanations, and facility drill-down with time-series charts.
**FRs covered:** FR17–FR22, FR26–FR28, NFR1–NFR2

### Epic 4: Multi-Hub Overview & Export (Tabs 2 & 4)
The Programme Manager sees all 5 networks simultaneously; IT/Data team compares scenarios and exports PNG; presenter has Cloud backup ready.
**FRs covered:** FR21, FR23–FR25, FR29, NFR3

### Epic 5: Demo Readiness — Testing, Performance & Rehearsal
The team enters the June 9–10 presentation with verified performance NFRs, 80% coverage, WCAG AA confirmed, and a completed demo rehearsal.
**FRs covered:** NFR1–NFR11, FR25

---

## Epic 1: Project Foundation

Any developer can clone the repo, install all dependencies, and have a contract test suite that defines exactly what the system must produce — before a single YAML or scenario exists. Gates all subsequent epics.

### Story 1.1: Project Initialisation

As a developer,
I want a fully configured Python project with all dependencies installed and a working .streamlit config,
So that every team member can run the app and tests from a clean checkout with a single command.

**Acceptance Criteria:**

**Given** an empty directory
**When** the developer runs `uv init diagnet_simul && cd diagnet_simul && uv add streamlit plotly networkx scipy pandas pyarrow pydantic pyyaml kaleido openpyxl && uv add --dev pytest pytest-cov ruff`
**Then** `uv run streamlit run app.py` launches without error (app.py may be a stub showing "DiagNet — coming soon")
**And** `uv run pytest` exits 0 (no tests yet — empty suite passes)
**And** `uv.lock` and `requirements.txt` (exported) are committed

**Given** the project is checked out on a machine with no internet
**When** `uv run streamlit run app.py` is executed
**Then** the app loads without fetching any external assets
**And** `.streamlit/config.toml` contains `server.headless = true` and `browser.gatherUsageStats = false`

### Story 1.2: Core Data Models

As a developer,
I want all shared TypedDicts and dataclasses defined in core/models.py,
So that generation pipeline and playback app share a single, explicit data contract with no ambiguity.

**Acceptance Criteria:**

**Given** `core/models.py` exists
**When** it is imported
**Then** the following are defined and importable: `FacilityState` (dataclass, 17 fields matching PRD §5.1 exactly including `daily_consumption`), `AlertRecord` (dataclass with tick, facility_id, network_id, alert_type, message, shap_contributions dict, severity), `ScenarioMeta` (TypedDict with id, display_name, tick_count, network_ids, parquet_path, alerts_path), `ScenarioPayload` (TypedDict with tick_df, alerts, metadata), `FlatTickSnapshot` (TypedDict with all 17 FacilityState fields plus derived metrics: betweenness_centrality, pagerank, bottleneck_score, effective_capacity_days, predicted_stockout_day)
**And** `safe_format(template: str, state_dict: dict) -> str` is defined; missing keys render as `[key_name]`
**And** `FlatTickSnapshot` field names exactly match the intended parquet column names (verified by inspection)

**Given** `FacilityState` is instantiated with all 17 fields
**When** `safe_format("{patients_queued:.0f} patients", state.__dict__)` is called
**Then** it returns the formatted string without raising
**And** `safe_format("{nonexistent_field}", state.__dict__)` returns `"[nonexistent_field]"` without raising

### Story 1.3: Contract Tests (Red State)

As a developer,
I want contract tests written and failing before any YAML or simulation code exists,
So that the test suite defines the correctness contract before implementation begins (red → green discipline).

**Acceptance Criteria:**

**Given** `tests/test_config_contract.py` exists
**When** run with `uv run pytest tests/test_config_contract.py`
**Then** tests FAIL with ImportError or FileNotFoundError (no YAML exists yet — this is intentional red state)
**And** the test file contains: `test_alert_tokens_resolve_against_facility_state` (loads all scenario YAMLs, checks every `{token}` in alert msg strings resolves against `FacilityState.__dict__`)

**Given** `tests/test_models.py` exists
**When** run after `core/models.py` is complete
**Then** all tests PASS including: `test_facility_state_has_17_fields`, `test_flat_tick_snapshot_field_count`, `test_safe_format_handles_missing_key`, `test_safe_format_formats_known_field`

**Given** `tests/conftest.py` exists
**When** imported
**Then** it provides fixtures: `dummy_facility_state` (valid FacilityState with all 17 fields), `dummy_alert_record`, `dummy_tick_df` (2-row DataFrame with FlatTickSnapshot columns)

---

## Epic 2: Scenario Data — All 8 Scenarios Pre-Computed

The presenter has all 8 playable scenarios committed to the repo. Any scenario selected from the dropdown has data ready to display. Covers the full pipeline: YAML configs → generation engine → committed parquet + JSON.

### Story 2.1: networks.yaml — All 59 Facilities

As a domain expert,
I want all 5 networks with their facilities, baselines, thresholds, and links defined in a single validated YAML file,
So that facility parameters can be adjusted without touching Python code.

**Acceptance Criteria:**

**Given** `config/networks.yaml` exists and is loaded
**When** parsed and validated by pydantic
**Then** exactly 5 networks (NET-A through NET-E) are present with correct facility counts: NET-A=14, NET-B=11, NET-C=13, NET-D=9, NET-E=12 (total 59)
**And** every facility has: display_name, type (hub/truenat/microscopy/chc), x/y canvas position, baseline dict (all applicable FacilityState fields including daily_consumption), thresholds dict (warn/critical per applicable field)
**And** intra-network links defined as [from, to, travel_time_minutes] triples
**And** top-level `inter_network_links` key with all 3 inter-network connections (NET-A↔NET-C, NET-B↔NET-D, NET-D→NET-A) each with source, target, source_facility, target_facility, travel_time_min, flow_type
**And** `uv run python -c "import yaml, pathlib; yaml.safe_load(pathlib.Path('config/networks.yaml').read_text())"` exits 0

**Given** `config/networks.yaml` contains a malformed threshold value
**When** pydantic validation runs during generation
**Then** a human-readable Pydantic ValidationError is raised naming the offending field and network

### Story 2.2: Scenario YAMLs — All 8 Scenarios

As a developer,
I want all 8 scenario YAML files defined with complete per_tick_deltas, shap_weights, alert sequences (matching PRD §6.2 tick tables), and recommended_actions,
So that the generation pipeline can produce all pre-computed outputs without any hardcoded values.

**Acceptance Criteria:**

**Given** `config/scenarios/sc-01.yaml` through `config/scenarios/sc-08.yaml` exist
**When** each is loaded and validated
**Then** every file contains: name, primary_network, max_ticks, affected_facilities list, per_tick_deltas dict, shap_weights dict, reroutes list, alerts list (each with tick, type, recipient, facility, msg), recommended_actions dict
**And** SC-08 includes an `initial_states` block with post-crisis baselines for all 5 networks
**And** every alert `msg` string uses only `{field_name}` tokens that exist in `FacilityState.__dict__`
**And** `tests/test_config_contract.py::test_alert_tokens_resolve_against_facility_state` passes GREEN for all 8 scenarios

**Given** SC-01 alert at tick 4 has `msg: "DHC queue critical: {patients_queued:.0f} patients, TAT {tat_hours:.0f}h"`
**When** `safe_format()` is called with a FacilityState where patients_queued=58 and tat_hours=34
**Then** returns `"DHC queue critical: 58 patients, TAT 34h"` exactly

### Story 2.3: Scenario Config Loader & Validator

As a developer,
I want generation/scenario_config.py to load and validate scenario YAMLs into typed Python objects,
So that the generation engine receives structured, validated config with no raw dict access.

**Acceptance Criteria:**

**Given** `generation/scenario_config.py` exists
**When** `load_scenario_yaml("config/scenarios/sc-01.yaml")` is called
**Then** returns a `ScenarioConfig` dataclass with all fields populated
**And** `validate_config(config)` raises a descriptive ValueError if per_tick_deltas reference facility IDs not in networks.yaml
**And** `validate_config(config)` raises if shap_weights keys don't match per_tick_deltas keys

**Given** a scenario YAML with a misspelled facility ID in affected_facilities
**When** `validate_config()` runs
**Then** raises `ValueError("Unknown facility 'DHC-X' in scenario SC-01 — not found in networks.yaml")`

### Story 2.4: Simulation Engine with AI Stubs

As a developer,
I want generation/engine.py to implement ScenarioGenerator with all 5 AI model stubs and produce correct FlatTickSnapshot rows per tick,
So that pre-computed outputs faithfully represent DiagNet's full capability stack.

**Acceptance Criteria:**

**Given** `ScenarioGenerator(scenario_config, network_config)` is instantiated with SC-01 config
**When** `.run()` is called
**Then** returns a list of `FlatTickSnapshot` dicts with exactly max_ticks × facility_count rows
**And** each row contains all FlatTickSnapshot fields with no None values for applicable fields
**And** `tick()` returns a new GlobalState object (not the same object — identity check: `s0 is not s1`)
**And** `apply_overflow()` adds overflow_pending values to target network hub's patients_queued

**Given** SC-01 config with DHC-A patients_queued delta of +1.8 per tick
**When** `.run()` is called for 4 ticks
**Then** DHC-A patients_queued at tick 4 ≈ baseline + (1.8 × 4) ± stochastic noise (within ±5%)

**Given** B1 stub is called for a facility with 10 cartridges and daily_consumption of 8
**When** stockout probability is computed
**Then** returns a float in range [0.20, 0.95]

**Given** M2 is called for a 14-facility network
**When** betweenness centrality is computed
**Then** every facility has a betweenness_centrality float in [0.0, 1.0]
**And** composite_bottleneck_score = 0.6 × normalized_betweenness + 0.4 × normalized_pagerank for every facility

**Given** M4 is called with a source and candidate destinations
**When** Dijkstra path is computed using composite edge weight (travel_time + tat_penalty)
**Then** returns ordered list of facilities with estimated TAT per route

### Story 2.5: SHAP Calculator

As a developer,
I want generation/shap_calculator.py to compute SHAP contributions per alert and embed them in AlertRecord objects,
So that every alert in the pre-computed output has mathematically consistent, readable SHAP explanations.

**Acceptance Criteria:**

**Given** `compute_shap(delta=1.8, weight=0.45)` is called
**When** executed
**Then** returns 0.81 (delta × weight exactly)

**Given** `generate_alert_shap(alert_config, facility_state, scenario_config)` is called for SC-01 tick 4
**When** executed
**Then** returns dict with keys matching shap_weights fields, values = per_tick_delta × weight × ticks_elapsed
**And** contributions are sorted by absolute value descending
**And** result matches worked example: patients_queued=3.24, tat_hours=0.84, cascade_dropout_risk=0.032 (±0.01)

**Given** a facility not in affected_facilities
**When** SHAP is computed
**Then** returns empty dict (no contributions for unaffected facilities)

### Story 2.6: Scenario Generation CLI + Commit Data

As a developer,
I want scripts/generate_scenarios.py to produce validated parquet + JSON outputs for all 8 scenarios with a single command,
So that `data/scenarios/` can be regenerated in < 30 seconds during the sprint if YAML configs change.

**Acceptance Criteria:**

**Given** all YAML configs are valid
**When** `uv run python scripts/generate_scenarios.py --all --validate` runs
**Then** exits 0 and produces: `data/scenarios/metadata.json` + 8 × parquet files + 8 × alert JSON files (17 files total)
**And** `metadata.json` contains schema_version, scenarios array with id/display_name/tick_count/parquet_path/alerts_path for all 8
**And** each parquet file has shape (max_ticks × facility_count, 22 columns) where 22 = 17 FacilityState fields + 5 derived metrics
**And** each alert JSON is a valid list of AlertRecord dicts with shap_contributions embedded
**And** total size of all parquet files < 500KB (snappy compressed)

**Given** `--scenario SC-03` flag is passed
**When** the script runs
**Then** regenerates only SC-03 outputs and updates metadata.json accordingly

**Given** a YAML config has an alert token referencing a non-existent FacilityState field
**When** `--validate` flag is used
**Then** exits 1 with error message naming the offending token, scenario, and tick

**Given** `tests/test_generation.py` runs against committed data
**When** SC-01 is regenerated with seed=42 and compared against sc-01_golden.json fixture
**Then** tick history values match to 4 decimal places for all 5 ticks

---

## Epic 3: Primary Demo View — Network Map + Facility Detail

The DTO and Lab Supervisor watch the core demo: network map updating tick-by-tick with alerts and SHAP explanations, and facility drill-down with time-series charts. Covers viz components, playback infrastructure, and Tabs 1 & 3.

### Story 3.1: Network Map Figure Builder

As a developer,
I want viz/network_map.py to produce correctly encoded Plotly network figures from FlatTickSnapshot data,
So that Tab 1 and Tab 2 can render accurate, visually consistent network maps without any simulation logic.

**Acceptance Criteria:**

**Given** `build_network_figure(tick_df, tick, network_id, selected_facility, active_reroutes)` is called with valid data
**When** the figure is returned
**Then** returns `go.Figure` with node traces encoding: size (hub=30px, truenat=22px, microscopy=16px, chc=12px), colour (#22c55e ok / #f59e0b warning / #ef4444 critical / grey offline)
**And** critical nodes have a second scatter trace as static outer ring at 1.5× radius with 0.4 opacity
**And** active reroute edges rendered as blue dashed lines
**And** each node has a hover tooltip showing facility display_name and all applicable metric values

**Given** `tick_df` is an empty DataFrame
**When** `build_network_figure()` is called
**Then** returns `go.Figure()` without raising any exception

**Given** `build_mini_map(tick_df, tick, network_id)` is called
**When** executed
**Then** returns `go.Figure` at approximately 200×200px with simplified node encoding (no tooltips, colour-only status)

### Story 3.2: Alert Card & SHAP Renderer

As a developer,
I want viz/alerts.py to render alert cards with embedded SHAP bars from AlertRecord objects,
So that every alert displayed in the app has a consistent, WCAG AA-compliant format with SHAP explanation.

**Acceptance Criteria:**

**Given** `build_alert_cards(alerts, max_cards=14)` is called with a list of AlertRecords
**When** executed
**Then** returns HTML string with at most 14 cards, ordered most-recent-first
**And** CRITICAL cards use background #dc2626, white text; DTO ADVISORY uses #fef3c7 background with #92400e text; BAYESIAN uses #eff6ff background with #1e40af text
**And** each card shows: alert type badge, tick timestamp, message text, 2-line SHAP summary from top-2 shap_contributions

**Given** `format_shap_bar(shap_contributions, top_n=2)` is called with {"patients_queued": 3.24, "tat_hours": 0.84}
**When** executed
**Then** returns string "↑ Queue load (+3.24) · ↑ TAT (+0.84)"

**Given** `build_alert_cards([])` is called (empty list)
**When** executed
**Then** returns HTML string containing the text "No alerts — simulation not started."

### Story 3.3: Session State & Playback Engine

As a developer,
I want session.py and playback.py to define all session_state keys as constants and implement the tick cursor advancement loop,
So that no module in the app uses raw session_state string keys and the playback loop is testable in isolation.

**Acceptance Criteria:**

**Given** `session.py` exists
**When** imported
**Then** exports constants: SCENARIO_DATA, CURRENT_SCENARIO, TICK_CURSOR, IS_PLAYING, SELECTED_FACILITY, SCENARIO_SNAPSHOTS, GRAPH_CACHE, PERF_LOG (all string values matching the snake_case names)
**And** `init_session_state(scenario_data)` initialises all keys with correct types and defaults (TICK_CURSOR=0, IS_PLAYING=False, SELECTED_FACILITY=None)

**Given** `get_interval_s(speed_multiplier)` is called
**When** speed_multiplier = 0.5, 1.0, 2.0, 4.0
**Then** returns 1.6, 0.8, 0.4, 0.2 respectively

**Given** `advance_tick(current_tick, max_ticks)` is called with current_tick=34, max_ticks=35
**When** executed
**Then** returns 34 (not 35 — bounds-checked, never exceeds max_ticks - 1)
**And** `advance_tick(10, 35)` returns 11

### Story 3.4: App Startup & Data Loading

As a developer,
I want app.py to validate all pre-computed data at startup, load all 8 scenarios eagerly, and halt with a clear error if data is missing,
So that the demo never starts in a corrupt state and missing data is immediately actionable.

**Acceptance Criteria:**

**Given** all 8 parquet files and metadata.json exist in data/scenarios/
**When** `uv run streamlit run app.py` is executed
**Then** app loads without error and session_state[SCENARIO_DATA] contains 8 ScenarioPayload entries
**And** startup completes (first render) in < 500ms on demo hardware

**Given** one parquet file is missing from data/scenarios/
**When** app starts
**Then** displays `st.error("Pre-computed data missing. Run: uv run python scripts/generate_scenarios.py --all")` and calls `st.stop()`
**And** no other content is rendered

**Given** app loads successfully
**When** user selects a scenario from the dropdown
**Then** session_state[CURRENT_SCENARIO] updates immediately and Tab 1 renders tick 0 of the new scenario

### Story 3.5: Persistent Top Bar & Playback Controls

As a presenter,
I want fully functional Play/Pause/Rewind controls with a Playback Speed slider and real-time tick counter,
So that I can control the demo narrative — pausing on key moments and advancing at the right pace.

**Acceptance Criteria:**

**Given** the app is loaded at tick 0
**When** the Play button is clicked
**Then** session_state[IS_PLAYING] = True and the tick counter advances every interval_s seconds
**And** the graph and alert panel update on every tick advance

**Given** the simulation is playing at tick 10
**When** the Pause button is clicked
**Then** session_state[IS_PLAYING] = False and tick counter freezes immediately (within one rerun cycle)

**Given** the simulation is at tick 15
**When** the Rewind button is clicked
**Then** session_state[TICK_CURSOR] = 0, IS_PLAYING = False, SELECTED_FACILITY = None
**And** scenario_snapshots[current_scenario] is preserved (not cleared)

**Given** the Playback Speed slider is set to 4×
**When** the simulation plays
**Then** ticks advance every ~0.2 seconds
**And** per-tick data values are identical to 1× playback (speed does not scale deltas)

**Given** the tick counter reaches max_ticks - 1
**When** one more tick would advance
**Then** IS_PLAYING = False and tick counter shows max_ticks - 1 (does not overflow)

### Story 3.6: Tab 1 — Network Map with Alert Panel & Tab 3 — Facility Detail

As a Lab Supervisor or DTO,
I want to see a live-updating network map with colour-coded facility nodes and a scrolling alert panel,
So that I can identify at a glance which facilities are at risk and what the system recommends.

**Acceptance Criteria:**

**Given** Tab 1 is active at tick 0
**When** rendered
**Then** Plotly network map shows all facilities for the selected network with correct tier sizes and green node colours
**And** alert panel shows "No alerts — simulation not started."
**And** metrics bar shows 5 cards (Critical sites, At-risk sites, Total patients queued, Low-cartridge sites, Avg cascade dropout risk %) all at baseline values

**Given** SC-01 is playing and reaches tick 4
**When** the CRITICAL alert fires (patients_queued > 50 AND tat_hours > 30 at DHC-A)
**Then** DHC-A node turns red (#ef4444) with static outer ring visible
**And** alert panel adds a CRITICAL card at the top with message, tick timestamp, and top-2 SHAP contributors
**And** global alert badge in the top bar shows count ≥ 1 in red

**Given** SC-01 reaches tick 7
**When** the RECOMMENDATION fires for reroute
**Then** blue dashed edges appear from MC2-A and CHC2-A to TL2-A

**Given** a node is clicked on the Plotly chart
**When** the click event fires
**Then** session_state[SELECTED_FACILITY] = clicked facility_id

**Given** SELECTED_FACILITY is set and user switches to Tab 3
**When** Tab 3 renders
**Then** shows facility display_name as header with current status badge
**And** 4 Plotly line charts render full tick history for: patients_queued, cartridges, TAT, cascade_dropout_risk — each with threshold lines at warn and critical values
**And** SHAP waterfall shows top-5 shap_contributions from the most recent alert for this facility, labelled "Approximate · simulation mode"
**And** recommended_actions section shows 3 pre-authored strings from the scenario YAML

**Given** SELECTED_FACILITY = None
**When** Tab 3 renders
**Then** shows "Click any node on the Network Map to open facility detail."

**Given** DHC-A is selected during SC-01 at tick 14
**When** SHAP waterfall renders
**Then** patients_queued bar = +3.24 and tat_hours bar = +0.84 (matching PRD §7 worked example)

---

## Epic 4: Multi-Hub Overview & Export — Tabs 2 & 4

The Programme Manager sees all 5 networks simultaneously; the IT/Data team compares scenarios and exports PNG; the presenter has a Streamlit Cloud backup ready.

### Story 4.1: Tab 2 — Multi-Hub Overview

As a Programme Manager,
I want to see all 5 networks simultaneously in a heatmap grid with inter-network flow indicators,
So that I can identify system-wide cascade risk and cross-district pressure in a single view.

**Acceptance Criteria:**

**Given** Tab 2 is active at any tick
**When** rendered
**Then** 5-column grid shows mini-maps for NET-A through NET-E, each ~200×200px, rendered from pre-computed parquet data for the current tick
**And** colour encoding is consistent with Tab 1 (green/amber/red by facility status)
**And** system-wide heatmap (bar chart) shows composite_bottleneck_score for all 59 nodes sorted descending
**And** global alert feed shows combined alert stream across all networks with network ID badge on each card

**Given** SC-04 is playing and NET-D overflow to NET-A is active at tick 8
**When** Tab 2 renders
**Then** inter-network flow arrow from NET-D to NET-A is visible and coloured red (critical flow)

**Given** "Run SC-08" button is clicked
**When** executed
**Then** CURRENT_SCENARIO = "sc-08", TICK_CURSOR = 0, IS_PLAYING = True
**And** all 5 mini-maps begin advancing simultaneously from SC-08 post-crisis baselines

**Given** Tab 2 renders with all 5 networks at tick 35
**When** performance is measured
**Then** full Tab 2 render completes in < 400ms (mini-maps read from session_state[SCENARIO_DATA] — no recomputation)

### Story 4.2: Tab 4 — Scenario Comparison & Export

As an IT/Data team member,
I want to compare two completed scenarios and export the network map as a PNG,
So that I can demonstrate the data feasibility of DiagNet to technical reviewers and produce slide assets.

**Acceptance Criteria:**

**Given** Tab 4 is active and two scenarios have been run to completion (saved in scenario_snapshots)
**When** the user selects Scenario A = SC-01 and Scenario B = SC-03 and metric = "patients_queued" from dropdowns
**Then** a dual-line Plotly chart renders showing patients_queued over ticks for both scenarios
**And** lines are distinctly coloured and labelled with scenario display_names

**Given** the "Download config" button is clicked in the config viewer
**When** executed
**Then** browser downloads `networks.yaml` as a file attachment

**Given** the simulation is paused and the screenshot button is clicked
**When** `DIAGNET_SCREENSHOT_ENABLED` env var is true (or not set)
**Then** `plotly.io.write_image(fig, "diagnet_screenshot.png", engine="kaleido", width=1920, height=1080)` executes
**And** a 1920×1080 PNG of the active Tab 1 network map figure is saved locally
**And** `st.success("Screenshot saved: diagnet_screenshot.png")` is displayed

**Given** `DIAGNET_SCREENSHOT_ENABLED=false`
**When** screenshot button is clicked
**Then** screenshot is not attempted and `st.info("Screenshot disabled in this environment.")` is shown

### Story 4.3: Streamlit Cloud Deployment

As the project lead,
I want the app deployed to Streamlit Cloud as a documented backup,
So that a laptop failure during the presentation does not end the demo.

**Acceptance Criteria:**

**Given** `requirements.txt` is committed (uv-exported) and `data/` is committed
**When** the app is deployed to Streamlit Cloud from the main branch
**Then** the app loads without error and all 8 scenarios play correctly in the Cloud deployment
**And** `DIAGNET_SCREENSHOT_ENABLED=false` is set in Streamlit Cloud secrets
**And** the Cloud URL is documented in README.md

**Given** `DIAGNET_SCREENSHOT_ENABLED=false` is active on Cloud
**When** screenshot button is clicked
**Then** `st.info("Screenshot disabled in this environment.")` is shown without error

---

## Epic 5: Demo Readiness — Testing, Performance & Rehearsal

The team enters June 9–10 with verified performance NFRs, 80% coverage, WCAG AA confirmed, and a completed demo rehearsal checklist.

### Story 5.1: Complete Test Suite to Coverage Gate

As a developer,
I want the full pytest suite to pass at ≥80% line coverage on core/ and generation/ modules,
So that the team has a regression safety net before the hackathon demo.

**Acceptance Criteria:**

**Given** all code modules are complete
**When** `uv run pytest --cov=core --cov=generation --cov-fail-under=80` runs
**Then** exits 0 with coverage ≥ 80% on core/ and generation/
**And** all tests in tests/test_models.py, test_data_generator.py, test_config_contract.py, test_engine.py, test_shap_calculator.py, test_network_map.py, test_alerts.py pass

**Given** `tests/test_generation.py::test_scenario_golden_fixture[sc-01]` runs
**When** SC-01 is regenerated with seed=42 and compared against tests/fixtures/sc-01_golden.json
**Then** all tick × facility values match to 4 decimal places for ticks 0–4

### Story 5.2: Performance Validation

As a developer,
I want the tick playback and data load NFRs verified with actual measurements on demo hardware,
So that the team knows before the demo whether any optimisation is needed.

**Acceptance Criteria:**

**Given** all 8 parquets are loaded at startup
**When** startup time is measured from `uv run streamlit run app.py` to first render
**Then** startup completes in < 500ms on the demo laptop

**Given** the playback loop is running at 4× speed
**When** tick render time is measured (time from is_playing=True rerun to next rerun)
**Then** median tick render latency < 400ms across 20 ticks

**Given** `uv run pytest tests/test_export.py::test_json_serialisation_benchmark` runs
**When** full tick history (35 ticks × 59 facilities × 22 fields) is serialised to JSON
**Then** completes in < 500ms

### Story 5.3: WCAG AA Audit, Offline Test & Demo Rehearsal

As the project lead,
I want a full demo rehearsal run verifying all 3 success criteria and a manual WCAG audit of alert card colours,
So that the team enters the June 9–10 presentation with confidence.

**Acceptance Criteria:**

**Given** all 8 scenarios are pre-computed and the app is running locally
**When** the demo rehearsal checklist is run
**Then** all 8 scenarios complete (Play → max_ticks) without a Python traceback visible to the audience
**And** at least 1 SHAP panel is visible on an alert card per scenario
**And** Tab 2 renders all 5 networks simultaneously without perceptible lag

**Given** alert cards are rendered in Chrome ≥120
**When** contrast ratios are measured manually (browser DevTools or contrast checker)
**Then** CRITICAL cards (#dc2626 bg / white text) pass WCAG AA (≥4.5:1 for normal text)
**And** DTO ADVISORY cards (#fef3c7 bg / #92400e text) pass WCAG AA
**And** BAYESIAN cards (#eff6ff bg / #1e40af text) pass WCAG AA

**Given** the app is running with no internet connection
**When** all 4 tabs are navigated and all 8 scenarios are played
**Then** no CDN requests are made and all functionality works offline
