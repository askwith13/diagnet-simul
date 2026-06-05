---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-06-04'
inputDocuments:
  - "_bmad-output/planning-artifacts/Simulation PRD.md"
workflowType: 'architecture'
project_name: 'DiagNet_Simul'
user_name: 'Aswath'
date: '2026-06-04'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Core Architectural Decision: Pre-Computed Outputs

**Decision (locked):** DiagNet_Simul is a **playback application**, not a live simulation engine. All scenario outputs are pre-computed offline by a generation pipeline and committed to the repository. The Streamlit app is a pure reader. This decision was made to eliminate traceback risk during the demo and reduce Streamlit session-state complexity.

This decision splits the system into two distinct layers sharing a data contract:

- **Layer 1 — Generation Pipeline** (runs once, offline, before demo): simulation engine, NetworkX graph analytics, SHAP computation, YAML config loading, parquet + JSON output writers.
- **Layer 2 — Streamlit Playback App** (pure reader): loads pre-computed data at startup, advances a tick cursor, renders Plotly figures from flat DataFrames.

### Requirements Overview

**Functional Requirements:**

35+ FRs across 5 categories: (1) multi-hub network topology — 5 networks, 59 nodes, 3 inter-network links; (2) facility data model — 17-field FacilityState, NetworkState, GlobalState with overflow coordination (generation-only); (3) scenario engine — 8 YAML-driven scenarios, each with scripted alert sequences and per_tick_deltas (generation-time); (4) AI model stubs — B1 Bayesian stockout, B2 cascade dropout lookup, M1 Z-score anomaly, M2 graph analytics, M4 Dijkstra router — all computed at generation time, outputs stored in parquet/JSON; (5) 4-tab Streamlit dashboard — Network Map, Multi-Hub Overview, Facility Detail, Analytics & Export.

**Non-Functional Requirements:**

- Tick playback latency < 400ms at 4× speed (now a cursor increment + `st.rerun()`, not simulation math)
- JSON/parquet load < 500ms at startup (< 500KB total pre-computed data)
- All 5 networks renderable on Tab 2 simultaneously (reads `summary.json` per network — pre-aggregated)
- Same scenario always plays identically (deterministic: pre-computed)
- Fully offline with bundled assets (kaleido, Plotly JS)
- WCAG AA for alert cards

**Scale & Complexity:**

- Primary domain: Python data pipeline + Streamlit playback web UI
- Complexity level: High for generation pipeline; Medium for playback app
- Estimated components: 8 generation modules + 4-tab playback app + data contract layer
- Total pre-computed data volume: ~500KB (8 scenarios × ~60KB snappy-compressed parquet + alert JSON)

### Technical Constraints & Dependencies

**Generation pipeline** (build-time only): NetworkX ≥ 3.2, scipy.stats, PyYAML + pydantic, numpy + pandas, pyarrow

**Playback app** (runtime only): Streamlit ≥ 1.35, Plotly Graph Objects, pandas + pyarrow, kaleido, json stdlib

**Streamlit constraints:**
- `st.tabs()` has no programmatic tab-switching API — Tab 3 facility detail uses `session_state.selected_facility` set via `plotly_click` callback; user switches tab manually
- Plotly has no native per-node animation — critical nodes display static outer ring (v1)
- `session_state` holds only: `current_scenario`, `tick_cursor` (int), `loaded_data`, `is_playing` (bool)

**UI terminology (locked):** Play/Pause/Rewind (not Run/Pause/Reset); Playback Speed slider (not Simulation Speed); scenario comparison = Scenario A / Scenario B dropdowns (no snapshot-save flow)

**Cut from scope:** Excel export (removed); auto-pause on alert (out of scope)

### Cross-Cutting Concerns

1. **Data contract (FlatTickSnapshot)** — `FlatTickSnapshot` TypedDict in `core/models.py` is the single source of truth for parquet column names. Both the generation writer and the app reader import it. Schema drift between pipeline and app is the primary integration risk.
2. **SHAP computation is generation-only** — `shap_f = delta × weight` computed in `ScenarioGenerator`, stored in alert JSON. App reads SHAP values as plain floats; no SHAP math at runtime.
3. **GlobalState/NetworkState are generation-only internals** — never imported by the Streamlit app. The app's import surface is `pandas`, `pyarrow`, `streamlit`, `plotly`, `kaleido`, `json`.
4. **YAML as single source of truth** — facility baselines, thresholds, scenario deltas, SHAP weights, alert templates, inter-network links all live in YAML. Generation pipeline reads YAML; app never reads YAML at runtime.
5. **Alert token validation is generation-time** — `generate_scenarios.py --validate` checks all alert template tokens against `FacilityState.__dict__` before writing outputs. App trusts alert JSON as validated artifacts.

## Starter Template Evaluation

### Primary Technology Domain

Python data pipeline + Streamlit playback application. No community starter template applies — scaffold defined directly.

### Scaffold Decisions

**Package manager:** `uv` (already installed, v0.11.18) — pip-compatible, lockfile committed, single cold-install command on demo hardware.

**Python version:** 3.12.3 (system interpreter)

**Project structure:**
```
diagnet_simul/
├── pyproject.toml
├── uv.lock
├── config/
│   ├── networks.yaml
│   └── scenarios/sc-01.yaml … sc-08.yaml
├── core/
│   ├── models.py             # FlatTickSnapshot TypedDict + FacilityState dataclass
│   └── data_generator.py     # baseline state seeding
├── generation/               # build-time only — NEVER imported by app
│   ├── engine.py
│   ├── scenario_config.py
│   └── shap_calculator.py
├── scripts/
│   └── generate_scenarios.py # CLI: --all | --scenario SC-01 | --validate
├── data/scenarios/           # committed pre-computed outputs
│   ├── metadata.json
│   ├── sc-01_bottleneck.parquet
│   ├── sc-01_bottleneck_alerts.json
│   └── … (8 × parquet + alerts JSON)
├── viz/
│   ├── network_map.py        # stateless Plotly builder
│   └── alerts.py             # alert card renderer
├── app.py                    # Streamlit entry point
├── tests/
└── .streamlit/config.toml    # headless=true, no usage stats
```

**Key structural rule:** `generation/` is a top-level package. Any `import generation.*` inside `app.py` or `viz/` is a boundary violation — visible immediately from the import path.

**Initialization commands:**
```bash
uv init diagnet_simul && cd diagnet_simul
uv add streamlit plotly networkx scipy pandas pyarrow pydantic pyyaml kaleido openpyxl
uv add --dev pytest pytest-cov ruff
uv run python scripts/generate_scenarios.py --all --validate   # generate data
uv run streamlit run app.py                                     # launch app
uv run pytest --cov=core --cov=generation --cov-fail-under=80  # run tests
```

**Linting:** `ruff` (replaces flake8 + black + isort, zero config for hackathon defaults)

## Core Architectural Decisions

### Decision Priority Analysis

**Critical (block implementation):**
- Pre-computed two-layer architecture: generation pipeline (offline) + playback app (pure reader)
- `FlatTickSnapshot` TypedDict as the data contract between layers — parquet columns must match field names exactly
- `generation/` import boundary — never imported by `app.py`, `viz/`, or `core/`

**Important (shape architecture):**
- Parquet loading: eager, all 8 scenarios at startup into `session_state.scenario_data`
- Playback loop: `st.rerun()` + `time.sleep(interval_s)`
- Missing data: hard fail at startup with actionable error + `st.stop()`
- Deployment: local laptop primary; Streamlit Cloud backup (kaleido disabled via env var)

**Deferred (post-hackathon v2):**
- brms/Stan/rpy2 Bayesian upgrade; GCN/node2vec (M3); auto-pause on alert; Excel export

### Data Architecture

**Scenario loading — Eager at startup.**
All 8 scenario parquets + alert JSONs loaded into `st.session_state.scenario_data: Dict[str, ScenarioPayload]` on first run. `metadata.json` read first as the manifest. Total < 500KB; startup cost negligible.

```python
class ScenarioPayload(TypedDict):
    tick_df: pd.DataFrame       # parquet rows: tick × facility, all 17 fields + derived
    alerts: List[AlertRecord]   # parsed alert JSON, SHAP contributions embedded
    metadata: ScenarioMeta      # display_name, tick_count, network_ids
```

YAML read exclusively by generation pipeline. App never reads YAML at runtime.

**Missing data — hard fail**
```python
for scenario in metadata["scenarios"]:
    if not Path(scenario["parquet_path"]).exists():
        st.error("Pre-computed data missing. Run: "
                 "uv run python scripts/generate_scenarios.py --all")
        st.stop()
```

### Frontend Architecture (Streamlit)

**Playback loop**
```python
if st.session_state.is_playing:
    time.sleep(interval_s)
    st.session_state.tick_cursor += 1
    if st.session_state.tick_cursor >= max_ticks:
        st.session_state.is_playing = False
    st.rerun()
```
Speed to interval_s: 0.5x=1.6s, 1x=0.8s, 2x=0.4s, 4x=0.2s

**Session state schema (complete)**
```python
{
    "scenario_data":      Dict[str, ScenarioPayload],  # all 8, loaded at startup
    "current_scenario":   str,
    "tick_cursor":        int,
    "is_playing":         bool,
    "selected_facility":  Optional[str],               # set by plotly_click only
    "scenario_snapshots": Dict[str, pd.DataFrame],     # Tab 4 comparison
    "graph_cache":        Dict[str, Any],              # node layout positions
    "perf_log":           List[float],                 # debug mode only
}
```

Tab 3: `plotly_click` writes `selected_facility`; no programmatic tab switch; unset shows placeholder text.

### Infrastructure & Deployment

**Primary:** `uv run streamlit run app.py` — fully offline, kaleido bundled.
**Backup:** Streamlit Cloud — `requirements.txt` + `data/` committed; kaleido gated by `DIAGNET_SCREENSHOT_ENABLED` env var (false on Cloud). No CI/CD for hackathon; manual `git push` to deploy.

## Implementation Patterns & Consistency Rules

**7 rules all agents MUST follow:**

1. **session_state key constants from `session.py` only — never raw strings.**
   `from session import TICK_CURSOR, IS_PLAYING` etc. No `st.session_state["tick_cursor"]` inline.

2. **`viz/` functions are pure — no session_state reads or writes.**
   Every viz function signature takes explicit arguments and returns `go.Figure`. If it touches `st.session_state`, it's a bug.

3. **Never import from `generation/` in the playback app.**
   `app.py`, `viz/`, `tabs/`, `session.py`, `playback.py` — none of these may `import generation.*`.

4. **All viz functions return `go.Figure`, never dict or None. Handle empty data gracefully.**
   ```python
   if tick_df.empty:
       return go.Figure()  # not an exception
   ```

5. **Bounds-check `tick_cursor` before every increment.**
   ```python
   st.session_state[TICK_CURSOR] = min(st.session_state[TICK_CURSOR] + 1, max_ticks - 1)
   ```

6. **SHAP values are read from `AlertRecord.shap_contributions` — never recomputed in the app.**

7. **Parquet column names must exactly match `FlatTickSnapshot` field names** — verified by `tests/test_config_contract.py`.

### Naming Conventions
- All Python identifiers: `snake_case` (variables, functions, modules, parquet columns, session_state keys)
- Classes and TypedDicts: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- No camelCase anywhere

### Error Handling Tiers
- **Startup failures** (missing parquet, bad metadata): `st.error(msg)` + `st.stop()`
- **Runtime recoverable** (empty tick, missing facility): `st.warning(msg)`, app continues

### Alert JSON Schema (fixed — no variations)
```json
{
  "tick": 12, "facility_id": "DHC-A", "network_id": "NET-A",
  "alert_type": "critical", "message": "...",
  "shap_contributions": {"field": float},
  "severity": "critical"
}
```

### session_state Key Constants (`session.py`)
```python
SCENARIO_DATA      = "scenario_data"
CURRENT_SCENARIO   = "current_scenario"
TICK_CURSOR        = "tick_cursor"
IS_PLAYING         = "is_playing"
SELECTED_FACILITY  = "selected_facility"
SCENARIO_SNAPSHOTS = "scenario_snapshots"
GRAPH_CACHE        = "graph_cache"
PERF_LOG           = "perf_log"
```

## Project Structure & Boundaries

### Complete Project Directory

```
diagnet_simul/
├── pyproject.toml
├── uv.lock
├── requirements.txt                    # uv export --format requirements-txt (for Cloud)
├── .gitignore
├── README.md
├── .streamlit/
│   └── config.toml                     # server.headless=true, browser.gatherUsageStats=false
│
├── config/
│   ├── networks.yaml                   # 59 facilities, baselines, thresholds, links, inter-links
│   └── scenarios/
│       ├── sc-01.yaml … sc-08.yaml     # per_tick_deltas, shap_weights, alerts, reroutes
│
├── core/                               # shared — imported by BOTH generation and app
│   ├── __init__.py
│   ├── models.py                       # FlatTickSnapshot, FacilityState, AlertRecord,
│   │                                   # ScenarioPayload, ScenarioMeta, NetworkMeta
│   └── data_generator.py               # seed_baseline_states(config) → Dict[str, FacilityState]
│
├── generation/                         # build-time only — NEVER imported at runtime
│   ├── __init__.py
│   ├── engine.py                       # ScenarioGenerator, tick(), apply_overflow(),
│   │                                   # B1/B2/M1/M2/M4 stubs, NetworkX graph analytics
│   ├── scenario_config.py              # load_scenario_yaml() → ScenarioConfig, validate_config()
│   └── shap_calculator.py              # compute_shap(delta, weight), generate_alert_shap()
│
├── scripts/
│   └── generate_scenarios.py           # CLI: --all | --scenario SC-01 | --validate | --force
│
├── data/
│   └── scenarios/                      # committed pre-computed outputs
│       ├── metadata.json
│       ├── sc-01_bottleneck.parquet    + sc-01_bottleneck_alerts.json
│       ├── sc-02_stockout.parquet      + sc-02_stockout_alerts.json
│       ├── sc-03_bayesian.parquet      + sc-03_bayesian_alerts.json
│       ├── sc-04_cascade.parquet       + sc-04_cascade_alerts.json
│       ├── sc-05_multifailure.parquet  + sc-05_multifailure_alerts.json
│       ├── sc-06_downtime.parquet      + sc-06_downtime_alerts.json
│       ├── sc-07_surge.parquet         + sc-07_surge_alerts.json
│       └── sc-08_recovery.parquet      + sc-08_recovery_alerts.json
│
├── viz/                                # stateless Plotly builders — no session_state
│   ├── __init__.py
│   ├── network_map.py                  # build_network_figure(), build_mini_map()
│   └── alerts.py                       # build_alert_cards(), format_shap_bar()
│
├── session.py                          # session_state key constants + init_session_state()
├── playback.py                         # advance_tick(), get_interval_s(), speed_to_interval()
│
├── tabs/
│   ├── __init__.py
│   ├── network.py                      # render_network_tab(payload, tick, selected_facility)
│   ├── overview.py                     # render_overview_tab(all_payloads, tick)
│   ├── facility.py                     # render_facility_tab(payload, tick, facility_id)
│   └── export.py                       # render_export_tab(snapshots)
│
├── app.py                              # Streamlit entry — startup validation, tab routing, playback loop
│
└── tests/
    ├── __init__.py
    ├── conftest.py                     # fixtures: dummy_facility_state, dummy_payload, dummy_tick_df
    ├── fixtures/
    │   └── sc-01_golden.json           # 5-tick golden output for SC-01 regression
    ├── test_models.py                  # FlatTickSnapshot field count, TypedDict roundtrip
    ├── test_data_generator.py          # seeded output determinism, all fields populated
    ├── test_config_contract.py         # YAML alert tokens vs FacilityState.__dict__
    ├── test_engine.py                  # tick() returns new object, apply_overflow()
    ├── test_shap_calculator.py         # compute_shap(delta, weight) == delta * weight
    ├── test_network_map.py             # returns go.Figure, handles empty df
    ├── test_alerts.py                  # alert card render, SHAP bar format
    ├── test_generation.py              # full 5-tick run, golden fixture compare
    └── test_export.py                  # JSON serialisation < 500ms benchmark
```

### Architectural Boundaries

| Boundary | Mechanism | Violation signal |
|---|---|---|
| Generation ↔ App | File system (`data/scenarios/`) | `import generation.*` in app-side file |
| `core/` ↔ both layers | Python import (allowed both ways) | Importing `generation/` from `app.py` |
| `viz/` ↔ `tabs/` | Function arguments + `go.Figure` return | `st.session_state` inside `viz/` |
| `session.py` write rules | Constants + code review | Raw string key in `st.session_state[...]` |

### PRD Requirements → File Mapping

| PRD section | Lives in |
|---|---|
| §4 Network topology, inter-links | `config/networks.yaml`, `generation/engine.py` |
| §5 FacilityState, NetworkState, GlobalState | `core/models.py`, `generation/engine.py` |
| §6 Scenarios, YAML schema, alert sequences | `config/scenarios/*.yaml`, `generation/`, `data/scenarios/` |
| §7 AI stubs (B1–M4), SHAP | `generation/engine.py`, `generation/shap_calculator.py` |
| §8.3 Tab 1 — Network Map | `viz/network_map.py`, `tabs/network.py` |
| §8.4 Tab 2 — Multi-Hub Overview | `viz/network_map.py` (build_mini_map), `tabs/overview.py` |
| §8.5 Tab 3 — Facility Detail | `tabs/facility.py`, `viz/alerts.py` |
| §8.6 Tab 4 — Export & Comparison | `tabs/export.py` |
| §8.2 Playback controls, speed slider | `playback.py`, `session.py`, `app.py` |
| §9 NFRs (perf, screenshot, offline) | `playback.py` (perf_log), `tabs/export.py` (kaleido) |
| §10 Tests | `tests/` — full map in tree above |

### Data Flow

```
config/*.yaml
    ↓  [generation pipeline — build time]
generation/engine.py + shap_calculator.py
    ↓
data/scenarios/*.parquet + *_alerts.json + metadata.json
    ↓  [file system boundary]
app.py startup → session_state[SCENARIO_DATA]
    ↓
playback.py → session_state[TICK_CURSOR]
    ↓
tabs/*.py → viz/*.py → go.Figure → st.plotly_chart()
```

## Architecture Validation

### Coherence — PASS

All technology choices are compatible: Python 3.12 + uv + Streamlit ≥1.35 + Plotly + pandas/pyarrow + kaleido form a well-established stack with no version conflicts. The `generation/` import boundary is consistent throughout — the structure, the patterns, and the file mapping all enforce it the same way. Pattern conventions (snake_case, pure viz, session_state constants) are internally consistent and align with Python/Streamlit idioms.

One coherence note resolved: `app.py` (flat file) and `tabs/` (subdirectory) are separate — no `app/` package conflict.

### Requirements Coverage — PASS

All 35+ PRD functional requirements map to specific files (see table above). All 8 NFRs addressed:

| NFR | Architectural mechanism |
|---|---|
| <400ms tick render | Eager load at startup; cursor increment only in playback loop |
| <500ms JSON serialisation | Flat tick_history dicts; no nested objects |
| 5 networks on Tab 2 | Pre-computed summary in parquet; build_mini_map() reads cached data |
| Reproducibility | Pre-computed outputs are deterministic by definition |
| Offline | kaleido bundled; no CDN; data committed to repo |
| WCAG AA | Colour pairs specified in PRD §9; applied in viz/alerts.py |
| Browser compat | Streamlit handles; no custom JS |
| Config validation | Pydantic at generation time; --validate flag |

### Implementation Readiness — PASS

- All 16 checklist items confirmed below
- 7 mandatory agent rules documented with examples
- Complete file tree with specific filenames (no placeholders)
- PRD → file mapping table covers all sections
- 5 interface contracts specified by Amelia (contract tests written before feature code)

### Gap Analysis

**Minor gaps (do not block implementation):**

- `app.py` startup sequence order not written out as pseudocode — implementer can derive from: load metadata.json → validate paths (st.stop on fail) → load all 8 parquets → init_session_state() → render tabs
- `ScenarioMeta` and `NetworkMeta` TypedDict field lists not exhaustively enumerated — derive from metadata.json schema and parquet column list
- `conftest.py` fixture shapes described by name only — implementer creates minimal valid instances of each TypedDict

None of these are architectural decisions; they are implementation detail left appropriately to the developer.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed (step 2 — PRD v1.1 full analysis)
- [x] Scale and complexity assessed (High/Medium split across layers)
- [x] Technical constraints identified (Streamlit tab limits, Plotly animation, kaleido)
- [x] Cross-cutting concerns mapped (5 concerns documented)

**Architectural Decisions**
- [x] Critical decisions documented with versions (step 4 — all 4 decisions locked)
- [x] Technology stack fully specified (step 3 — uv + full package list)
- [x] Integration patterns defined (file system boundary, FlatTickSnapshot contract)
- [x] Performance considerations addressed (eager load, flat dicts, graph_cache)

**Implementation Patterns**
- [x] Naming conventions established (snake_case / PascalCase / UPPER_SNAKE_CASE)
- [x] Structure patterns defined (pure viz, session.py constants, generation boundary)
- [x] Communication patterns specified (session_state write rules, plotly_click)
- [x] Process patterns documented (error tiers, bounds-checking, SHAP read-only)

**Project Structure**
- [x] Complete directory structure defined (full tree, all files named)
- [x] Component boundaries established (4 boundaries with violation signals)
- [x] Integration points mapped (FlatTickSnapshot, metadata.json, file system)
- [x] Requirements to structure mapping complete (PRD § → file table)

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION**

**Confidence: High** — pre-computed architecture removes the largest sprint risk (Streamlit live simulation loop); all module contracts are specified; test strategy is concrete; no unresolved architectural decisions remain.

**Key strengths:**
- Two-layer separation eliminates runtime NetworkX/scipy dependency, making the playback app lightweight and robust under demo conditions
- FlatTickSnapshot as the single schema contract prevents drift between pipeline and app
- 7 mandatory agent rules with examples prevent the most common Python/Streamlit consistency failures
- All 8 scenarios have committed pre-computed data — demo traceback risk is near zero

**Areas for future enhancement (post-hackathon):**
- brms/Stan Bayesian upgrade (v2)
- GCN/node2vec embeddings (M3 → M4 pipeline)
- CI/CD pipeline with golden fixture regression on PR
- Streamlit multi-page app refactor for larger feature surface

### Implementation Handoff

**First implementation step:**
```bash
uv init diagnet_simul && cd diagnet_simul
uv add streamlit plotly networkx scipy pandas pyarrow pydantic pyyaml kaleido openpyxl
uv add --dev pytest pytest-cov ruff
```

Then, in module build order (PRD §10.2):
1. `core/models.py` — write `FlatTickSnapshot` TypedDict first; everything else derives from it
2. `tests/test_config_contract.py` — write contract test before any YAML exists (red state)
3. `config/networks.yaml` + `config/scenarios/*.yaml`
4. `core/data_generator.py`
5. `generation/engine.py` → `generation/shap_calculator.py`
6. `scripts/generate_scenarios.py --all --validate` → commit `data/`
7. `viz/network_map.py` → `viz/alerts.py`
8. `session.py` → `playback.py` → `tabs/*.py` → `app.py`
