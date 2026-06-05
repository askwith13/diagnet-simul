**DIAGNET**

Diagnostic Network Intelligence for TB Care

**Product Requirements Document**

_Version 1.1 · Multi-Hub Multi-Network Simulation Platform_

| **Document status**     | Updated — validation pass 2026-06-04                           |
| ----------------------- | -------------------------------------------------------------- |
| **Prepared by**         | DiagNet Team - PATH South Asia Digital Health                  |
| **Theme**               | 03 · AI in Healthcare Professionals Assistance                 |
| **Intended audience**   | Developers, Product Managers, Health System Architects         |
| **Stack**               | Python · Streamlit · Plotly · NetworkX · scipy · kaleido       |
| **Submission deadline** | 9-10 June 2026                                                 |

# 1\. Executive Summary

DiagNet is an AI-powered diagnostic network intelligence platform built for India's National TB Elimination Programme (NTEP). It ingests routine HMIS, LIS, referral, inventory, and outcomes data from NTEP-integrated infrastructure; constructs a live graph of the TB diagnostic ecosystem; and surfaces explainable, actionable interventions through clinician-facing nudges and District TB Officer (DTO) dashboards.

This document specifies requirements for a comprehensive, modular simulation platform that scales from the current single-district prototype (1 hub, 9 facilities) to a production-grade multi-hub, multi-network architecture spanning at least 5 independent CBNAAT hubs, each governing its own network of 5-15 subordinate facilities. The platform must faithfully reproduce the data flows, AI model outputs, and alert cascades of the full DiagNet production system in a demonstration environment, without requiring real patient data.

**One-line platform summary**

A Streamlit-based multi-hub network simulation that models 5+ CBNAAT hubs, 5+ facility networks (45-75 nodes total), 4 ML model layers, and 3 alert channels - all driven by synthetic NTEP-representative data and presented through an interactive Plotly network map with real-time Bayesian risk propagation.

## 1.1 Goals

- Demonstrate DiagNet's full capability stack to technical reviewers, health ministry officials, and PATH programme leadership in a single interactive session.
- Provide the DiagNet development team with a modular codebase that can be extended incrementally from simulation to live data integration.
- Serve as a teaching tool for non-technical stakeholders: the simulation should be comprehensible without a coding background.
- Establish architectural patterns (data model, graph engine, alert pipeline, dashboard layout) that carry forward to the production Python + Posit Connect cloud system.

**Demo success criteria**

The June demo is successful if: (a) all 8 scenarios complete without a Python traceback visible to the audience; (b) a SHAP panel is visible on at least one alert per scenario; (c) Tab 2 renders all 5 networks without perceptible lag.

## 1.2 Out of scope for v1.0

- Live connection to real NIKSHAY, DHIS2, or OpenELIS instances.
- Patient-identifiable data of any kind.
- Mobile interface (the platform is desktop-first for demonstration).
- Federated learning execution (the architecture is documented and simulated, not executed).
- In-app YAML editing with write-back (config is read-only in the dashboard; edits require offline file editing).
- Multi-user concurrent sessions, authentication, or real-time data ingestion from any external source.
- brms/Stan rpy2 integration (deferred to v2; v1 ships scipy stub only — see §3.3).

# 2\. Stakeholder Map & User Personas

The simulation platform serves two distinct audiences simultaneously: the live demo audience (non-technical health system stakeholders) and the development audience (the DiagNet team building the production system).

## 2.1 Primary demo audience

| **Persona**            | **Role**                                  | **What they need to see**                                           | **Key demo moment**                             |
| ---------------------- | ----------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------- |
| DTO / State TB Officer | District TB Officer overseeing programme  | Actionable alerts before a crisis, not after                        | Predicted stockout alert fires 14 days early    |
| Lab Supervisor         | Manages GeneXpert & microscopy operations | Queue lengths, TAT, cartridge stocks at their facility in real time | Node turns amber → tooltip shows exact metrics  |
| Programme Manager      | National / state NTEP leadership          | System-wide bottleneck view across all hubs simultaneously          | Multi-hub heatmap showing cascade risk gradient |
| IT / Data team         | Implements NTEP digital systems           | That the stack is feasible with existing data infrastructure        | Tab 4 tick history table and config download    |
| Funder / Reviewer      | PATH, GF, WHO evaluation committee        | That the AI outputs are explainable, not black-box                  | SHAP waterfall panel on any alert               |

## 2.2 Developer audience

| **Role**                          | **Primary module ownership**                   | **Needs from the codebase**                                                       |
| --------------------------------- | ---------------------------------------------- | --------------------------------------------------------------------------------- |
| AI / Product Designer (Mihir)     | Simulation engine, graph layer, scenario logic | Clean separation of state mutation and rendering; easy to add new scenarios       |
| Data & Research Analyst (Naveen)  | Synthetic data generator, Bayesian model stub  | Configurable facility parameters; exportable scenario logs                        |
| Tech Writing Lead (Dr Nitiksha)   | Alert text, legend copy                        | All user-facing strings in one constants file                                     |
| Domain Expert (Dr Lakshmi, Carel) | Facility configurations, cascade thresholds    | YAML/JSON config for facility types and alert thresholds - no code changes needed |
| Project Lead (Dr Aswath)          | End-to-end demo flow, presentation mode        | One-click scenario sequencing; screenshot/export capability                       |

# 3\. System Architecture

## 3.1 High-level module map

The application is organised into seven independent Python modules plus a configuration layer. Each module has a single responsibility and communicates through well-defined data contracts (Python dataclasses and dictionaries).

| **Module**            | **File**               | **Responsibility**                                                                             |
| --------------------- | ---------------------- | ---------------------------------------------------------------------------------------------- |
| Config layer          | config/networks.yaml   | All facility definitions, link topology, thresholds, alert text - edited without touching code |
| Data model            | core/models.py         | FacilityState, NetworkState, GlobalState, AlertRecord dataclasses; derived_status() logic      |
| Synthetic data engine | core/data_generator.py | Generates realistic baseline states + temporal noise for all 5 networks                        |
| Graph engine          | core/graph.py          | NetworkX graph construction, betweenness/PageRank, shortest-path routing                       |
| Simulation engine     | core/simulation.py     | Tick-based state mutation per scenario; Bayesian risk propagation; alert firing                |
| Visualisation layer   | viz/network_map.py     | Plotly figure builder: nodes, edges, reroute overlays, static ring markers, tooltips           |
| Alert pipeline        | viz/alerts.py          | Alert card renderer; notification categorisation (Critical / DTO / Bayesian)                   |
| Dashboard shell       | app.py                 | Streamlit page layout, session state, simulation loop, tab routing                             |

## 3.2 Data flow

The data flow follows a strict unidirectional pattern to ensure simulation state is always consistent and reproducible:

- config/networks.yaml is loaded once at startup into a validated Python dictionary.
- core/data_generator.py produces an initial NetworkState for each of the 5 networks, with stochastic noise applied to baseline metrics.
- On each tick, core/simulation.py receives the current GlobalState + scenario parameters and returns a new GlobalState plus a list of AlertRecords. No in-place mutation occurs outside this module.
- core/graph.py recomputes betweenness centrality and shortest-path routing on the updated state; results cached in `st.session_state.graph_cache[network_id][tick]` (plain dict — not `st.cache_data`).
- viz/network_map.py and viz/alerts.py consume the new state and render Plotly figures and HTML alert cards.
- app.py writes outputs to Streamlit placeholders, then sleeps for `interval_s / speed` before triggering `st.rerun()`.

**Architectural constraint — immutable tick state**

Each tick must produce a NEW state object, never mutate the previous one. This enables: (a) replay — the user can scrub back to any tick; (b) scenario comparison — two scenarios can be run and their states diffed; (c) export — the full tick history is serialisable to JSON for post-demo analysis.

## 3.3 Technology stack

| **Layer**             | **Technology**                    | **Rationale**                                                                  |
| --------------------- | --------------------------------- | ------------------------------------------------------------------------------ |
| UI framework          | Streamlit ≥ 1.35                  | Zero-infrastructure deployment; st.rerun() enables animation loop              |
| Network visualisation | Plotly Graph Objects              | Full hover control, custom marker shapes, edge styling; exportable to PNG      |
| Graph analytics       | NetworkX ≥ 3.2                    | Betweenness centrality, PageRank, Dijkstra; mirrors igraph R API in production |
| Bayesian model stub   | scipy.stats (v1 only)             | Posterior predictive distribution for stockout probability; brms/Stan deferred to v2 |
| Synthetic data        | numpy + pandas                    | Reproducible random seeds per network; exportable to CSV                       |
| Configuration         | PyYAML + pydantic                 | Schema-validated YAML; domain experts can edit without Python knowledge        |
| State management      | Python dataclasses + st.session_state | Typed, inspectable, serialisable                                           |
| Export                | plotly.io + openpyxl + kaleido    | PNG export of network map figure (kaleido required — must be bundled for offline); Excel export of tick history |

**v2 dependencies (not in v1 scope):** rpy2, brms, Stan.

# 4\. Multi-Hub Network Topology

## 4.1 Network definitions

The platform ships with 5 pre-configured district-level diagnostic networks, each representing a distinct epidemiological and infrastructural profile found across India's NTEP landscape.

| **Network ID** | **Hub name**                 | **Hub type**               | **Facilities** | **Profile**                                                   | **Key challenge**                               |
| -------------- | ---------------------------- | -------------------------- | -------------- | ------------------------------------------------------------- | ----------------------------------------------- |
| NET-A          | District Hospital Chandrapur | CBNAAT Hub (GeneXpert × 3) | 14             | Urban-dense, high volume, 3 microscopy centres, 4 CHCs        | Bottleneck: DHC overwhelmed by referral volume  |
| NET-B          | Truenat Hub Balaghat         | Truenat Hub (Truenat × 4)  | 11             | Semi-urban, moderate volume, mixed microscopy/Truenat feeders | Stockout: Cartridge drain under campaign surge  |
| NET-C          | District Hospital Yavatmal   | CBNAAT Hub (GeneXpert × 2) | 13             | Rural-sparse, long travel times, CHCs as primary entry        | Predicted stockout: Bayesian 14-day forecast    |
| NET-D          | Truenat Hub Gadchiroli       | Truenat Hub (Truenat × 2)  | 9              | Tribal / remote, very long travel, high dropout risk          | Cascade failure: Multiple simultaneous failures |
| NET-E          | District Hospital Amravati   | CBNAAT Hub + Culture Lab   | 12             | Mixed urban-rural, culture lab, DST referral chain            | Multi-failure: Stockout + bottleneck concurrent |

Total simulated facilities across all 5 networks: 59 nodes (5 hubs + 13 Truenat/secondary labs + 17 microscopy centres + 24 CHCs).

## 4.2 Facility type hierarchy

| **Tier** | **Facility type** | **Role in cascade**                                  | **Metrics that matter most**                              | **Typical count per network** |
| -------- | ----------------- | ---------------------------------------------------- | --------------------------------------------------------- | ----------------------------- |
| 1        | CBNAAT Hub (DHC)  | GeneXpert testing, DST referral, culture linkage     | TAT, machine uptime, modules, cartridges, queue           | 1                             |
| 2        | Truenat Lab       | Truenat MTB/RIF testing, pre-screening               | Truenat chips, TAT, HR, queue                             | 1-3                           |
| 3        | Microscopy Centre | Sputum smear, initial screening, specimen collection | Smear positivity rate, specimen rejection rate, HR        | 2-5                           |
| 4        | CHC / PHC         | First contact, presumptive TB ID, sample collection  | Patient throughput, referral completion, CHW availability | 3-8                           |

## 4.3 Inter-network connections

In addition to intra-network links, the platform models three inter-network connections representing real cross-district referral flows:

- NET-A ↔ NET-C (DHC Chandrapur → DHC Yavatmal): Culture and DST referral for complex cases.
- NET-B ↔ NET-D (Balaghat hub → Gadchiroli hub): Overflow referral when Gadchiroli capacity is exhausted.
- NET-D → NET-A (Gadchiroli → Chandrapur): High-risk / MDR-TB cases requiring full GeneXpert DST panel.

Inter-network links are defined in `config/networks.yaml` under a top-level `inter_network_links` key:

```yaml
inter_network_links:
  - source: NET-D
    target: NET-A
    source_facility: DHC-D
    target_facility: DHC-A
    travel_time_min: 240
    flow_type: overflow
```

**Why inter-network links matter**

The cascade failure scenario in NET-D (tribal/remote network) is only fully expressible when the inter-network link to NET-A is modelled - without it, the system cannot show the downstream pressure that Gadchiroli's failure places on Chandrapur. This is the key multi-hub insight that the single-network prototype cannot demonstrate.

# 5\. Facility Data Model

## 5.1 FacilityState fields

Every facility carries the following state fields. Fields not applicable to a given tier (e.g. GeneXpert modules at a CHC) are set to zero and excluded from tooltip display.

| **Field**                  | **Type** | **Unit**    | **Tooltip label**     | **Alert threshold (warn / critical)** |
| -------------------------- | -------- | ----------- | --------------------- | ------------------------------------- |
| patients_queued            | float    | count       | Patients queued       | \> 35 / > 55                          |
| cartridges                 | float    | count       | Cartridges            | < 25 / < 10                           |
| truenat_chips              | float    | count       | Truenat chips         | < 15 / < 5                            |
| travel_time_min            | float    | minutes     | Avg travel time       | Static baseline (no alert)            |
| tat_hours                  | float    | hours       | Sample TAT            | \> 24 h / > 36 h                      |
| hr_on_shift                | float    | staff count | HR on shift           | < 2 / < 1                             |
| machines                   | int      | count       | Machines              | \= 0 / - (facility offline)           |
| modules                    | int      | count       | Modules               | < 2 / < 1                             |
| samples_per_module_per_day | float    | samples     | Samples/module/day    | < 10 / < 5                            |
| daily_consumption          | float    | cartridges  | Daily consumption     | Static baseline (no alert)            |
| smear_positivity_rate      | float    | 0-1         | Smear positivity %    | \> 0.25 / > 0.40                      |
| specimen_rejection_rate    | float    | 0-1         | Specimen rejection %  | \> 0.15 / > 0.30                      |
| referral_completion_rate   | float    | 0-1         | Referral completion % | < 0.70 / < 0.50                       |
| chw_available              | int      | count       | CHW available         | < 1 / = 0                             |
| bayesian_stockout_prob     | float    | 0-1         | P(stockout 14d)       | \> 0.40 / > 0.70                      |
| cascade_dropout_risk       | float    | 0-1         | Cascade dropout risk  | \> 0.35 / > 0.60                      |
| status                     | enum     | -           | Status badge          | warning / critical                    |

## 5.2 Derived metrics computed per tick

- **network_betweenness_score** — fraction of inter-facility shortest paths passing through this node; high = chokepoint.
- **pagerank_score** — absorptive load: facilities attracting disproportionate referral volume score high.
- **composite_bottleneck_score** — 0.6 × normalised betweenness + 0.4 × normalised PageRank. Drives heatmap overlay.
- **effective_capacity_days** — `cartridges / daily_consumption`. Days of cartridge stock remaining at current consumption rate. (Applicable to CBNAAT and Truenat tiers only.)
- **throughput_capacity** — `modules × samples_per_module_per_day`. Maximum samples per day the facility can process. Displayed separately in tooltip; not combined with effective_capacity_days.
- **predicted_stockout_day** — MAP estimate from Bayesian B1 model; shown in tooltip and DTO alert. Derived from effective_capacity_days and the posterior uncertainty from B1.

## 5.3 NetworkState

A NetworkState object aggregates all FacilityState instances for one network plus graph metrics and the current tick:

```python
@dataclass
class NetworkState:
    network_id: str
    tick: int
    facilities: Dict[str, FacilityState]
    active_reroutes: List[Tuple[str, str]]
    alerts: List[AlertRecord]
    graph_metrics: Dict[str, float]       # betweenness, pagerank, bottleneck scores
    inter_network_links: List[Tuple[str, str, str]]  # (source_facility, target_facility, flow_type)
    scenario: Optional[str]
    tick_history: List[Dict]              # flat snapshots only — see note below
```

**tick_history format:** Each entry is a flat dict `{tick: int, facility_id: str, **facility_state_fields}`. The `tick_history` list stores only these flat dicts — it never contains nested NetworkState objects. This prevents O(n²) recursive growth when the tick history is serialised to JSON.

## 5.4 GlobalState

GlobalState holds all 5 NetworkStates and coordinates cross-network overflow. It is the top-level object owned by `app.py` and passed to `core/simulation.py` on each tick.

```python
@dataclass
class InterNetworkFlow:
    source_net: str
    target_net: str
    patient_count: float
    tick: int

@dataclass
class GlobalState:
    network_states: Dict[str, NetworkState]   # keyed by network_id (NET-A … NET-E)
    inter_network_flows: List[InterNetworkFlow]
    global_tick: int
    overflow_pending: Dict[str, float]        # keyed by target network_id
    scenario: Optional[str]
```

**Tick synchronisation:** All networks advance together on a single global tick (synchronous). `simulation.py` iterates over all networks in `GlobalState.network_states`, applies per-scenario deltas, then calls `GlobalState.apply_overflow()` which distributes `overflow_pending` to target networks before returning the new GlobalState. No async or per-network tick counters.

**Overflow propagation:** When a scenario delta pushes `patients_queued` above the critical threshold at a source facility, `simulation.py` adds the excess patient count to `overflow_pending[target_network_id]`. `apply_overflow()` adds this delta to the target hub's `patients_queued` on the same tick.

# 6\. Scenario Specifications

The platform ships with 8 simulation scenarios across the 5 networks. Each scenario has a defined trigger network, a progression model, and a scripted alert sequence. Scenarios are configured in `config/scenarios.yaml` and executed by `core/simulation.py` without code changes.

## 6.1 Scenario catalogue

| **ID** | **Name**                        | **Primary network** | **Type**   | **Max ticks** | **Narrative arc**                                                                  |
| ------ | ------------------------------- | ------------------- | ---------- | ------------- | ---------------------------------------------------------------------------------- |
| SC-01  | Network bottleneck              | NET-A (Chandrapur)  | Reactive   | 25            | DHC queue overwhelms → reroute fires → dropout risk peaks → DTO staffing advisory  |
| SC-02  | Gradual stockout                | NET-B (Balaghat)    | Reactive   | 25            | Truenat chip drain → cascade failure → emergency procurement advisory              |
| SC-03  | Predicted stockout (Bayesian)   | NET-C (Yavatmal)    | Preventive | 25            | Bayesian forecast fires at P=0.71 → preventive reroute → risk resolves             |
| SC-04  | Cascade failure + inter-network | NET-D (Gadchiroli)  | Reactive   | 30            | Multiple failures → cross-district overflow to NET-A → system-wide stress          |
| SC-05  | Concurrent multi-failure        | NET-E (Amravati)    | Reactive   | 30            | Stockout + bottleneck simultaneously → Dijkstra rerouting → partial recovery       |
| SC-06  | Machine downtime                | NET-A (Chandrapur)  | Reactive   | 20            | GeneXpert modules offline → TAT spikes → anomaly flag on test ordering             |
| SC-07  | Campaign month surge            | NET-B (Balaghat)    | Predictive | 25            | Seasonal demand spike → Bayesian model detects shift → proactive redistribution    |
| SC-08  | Full network recovery           | All 5 networks      | Recovery   | 35            | Post-crisis: interventions applied → all networks return to green → impact metrics |

**SC-08 start state:** Each network begins from a pre-loaded "post-crisis" YAML baseline defined in `config/scenarios.yaml` under `SC-08.initial_states`. These are fixed baselines, not derived from a prior scenario run. This avoids state dependency and makes SC-08 independently reproducible.

**SC-08 impact metrics** (displayed in Tab 4 at scenario completion): mean `composite_bottleneck_score` across all networks; total `patients_queued` reduction from tick 0 to tick 35; count of facilities returning to `status = ok`.

## 6.2 Alert sequences

### SC-01 — Network bottleneck (NET-A)

| **Tick** | **Alert type** | **Recipient**   | **Message summary**                                          | **Triggered by**                        |
| -------- | -------------- | --------------- | ------------------------------------------------------------ | --------------------------------------- |
| 4        | CRITICAL       | Lab Supervisor  | DHC queue critical: 58 patients, TAT 34 h (2× median)        | patients_queued > 50 AND tat_hours > 30 |
| 7        | RECOMMENDATION | Clinician       | Reroute MC2 & CHC-Central to TL-East. TAT relief 14 h        | bottleneck_score > 0.7 AND tick > 6     |
| 10       | CRITICAL       | CHW Coordinator | P(cascade dropout) = 0.74. CHW follow-up activation required | cascade_dropout_risk > 0.70             |
| 14       | DTO ADVISORY   | DTO             | Recommend +2 technicians + cartridge redistribution from TL2 | bottleneck persists > 10 ticks          |

### SC-02 — Gradual stockout (NET-B)

| **Tick** | **Alert type** | **Recipient**  | **Message summary**                                         | **Triggered by**                      |
| -------- | -------------- | -------------- | ----------------------------------------------------------- | ------------------------------------- |
| 5        | WARNING        | Lab Supervisor | Truenat chips at TL1-B: 14 remaining (< warn threshold)     | truenat_chips < 15                    |
| 12       | CRITICAL       | Lab Supervisor | Truenat chips critical: 4 remaining. Testing at risk        | truenat_chips < 5                     |
| 16       | DTO ADVISORY   | DTO            | Emergency procurement required: TL1-B chips exhausted in ~2d | predicted_stockout_day ≤ tick + 2   |
| 20       | CRITICAL       | DTO            | Cascade failure: TL1-B offline. Reroute to NET-D overflow   | machines = 0                          |

### SC-03 — Predicted stockout, Bayesian (NET-C)

| **Tick** | **Alert type**    | **Recipient** | **Message summary**                                         | **Triggered by**                     |
| -------- | ----------------- | ------------- | ----------------------------------------------------------- | ------------------------------------ |
| 6        | BAYESIAN          | DTO           | P(stockout in 14d) = 0.71 at DHC-C. Preventive action window | bayesian_stockout_prob > 0.70       |
| 9        | RECOMMENDATION    | DTO           | Preventive reroute activated: MC3-C → TL1-C for 7d         | bayesian_stockout_prob > 0.70 AND tick > 7 |
| 18       | BAYESIAN          | DTO           | P(stockout in 14d) = 0.28. Risk resolved by reroute         | bayesian_stockout_prob < 0.35        |

### SC-04 — Cascade failure + inter-network (NET-D → NET-A)

| **Tick** | **Alert type** | **Recipient** | **Message summary**                                              | **Triggered by**                              |
| -------- | -------------- | ------------- | ---------------------------------------------------------------- | --------------------------------------------- |
| 4        | CRITICAL       | Lab Supervisor | DHC-D queue critical: 48 patients                               | patients_queued > 45                          |
| 8        | CRITICAL       | DTO           | Machine failure at DHC-D. Overflow routing to NET-A activated    | machines = 0                                  |
| 12       | CRITICAL       | DTO (NET-A)   | Inter-network overflow: +22 patients arriving from NET-D         | GlobalState.overflow_pending['NET-A'] > 20    |
| 18       | DTO ADVISORY   | DTO           | System-wide stress: NET-A bottleneck_score 0.82. Emergency brief | composite_bottleneck_score > 0.80 (NET-A hub) |

### SC-05 — Concurrent multi-failure (NET-E)

| **Tick** | **Alert type** | **Recipient**  | **Message summary**                                        | **Triggered by**                                  |
| -------- | -------------- | -------------- | ---------------------------------------------------------- | ------------------------------------------------- |
| 3        | WARNING        | Lab Supervisor | Cartridges < 25 AND queue > 35 at DHC-E                   | cartridges < 25 AND patients_queued > 35          |
| 8        | CRITICAL       | DTO            | Dual failure: cartridges critical + queue critical         | cartridges < 10 AND patients_queued > 55          |
| 14       | RECOMMENDATION | Clinician      | Optimal reroute computed: CHC3-E → TL1-E (saves 11h TAT)  | M4 Dijkstra route available                       |
| 22       | DTO ADVISORY   | DTO            | Partial recovery: queue reduced, cartridges still critical | patients_queued < 40 AND cartridges < 10          |

### SC-06 — Machine downtime (NET-A)

| **Tick** | **Alert type** | **Recipient**  | **Message summary**                                    | **Triggered by**                |
| -------- | -------------- | -------------- | ------------------------------------------------------ | ------------------------------- |
| 2        | CRITICAL       | Lab Supervisor | GeneXpert module 2 offline at DHC-A. TAT rising        | modules < 2                     |
| 6        | BAYESIAN       | Lab Supervisor | Anomaly score 0.81: test-ordering pattern abnormal     | M1 anomaly_score > 0.75         |
| 12       | DTO ADVISORY   | DTO            | TAT 38h exceeds critical threshold. Engineer dispatch  | tat_hours > 36                  |

### SC-07 — Campaign month surge (NET-B)

| **Tick** | **Alert type** | **Recipient** | **Message summary**                                       | **Triggered by**                          |
| -------- | -------------- | ------------- | --------------------------------------------------------- | ----------------------------------------- |
| 4        | BAYESIAN       | DTO           | P(stockout in 14d) rising: 0.55. Campaign surge detected  | bayesian_stockout_prob > 0.50             |
| 8        | RECOMMENDATION | DTO           | Proactive chip redistribution: TL3-B → TL1-B (20 chips)  | bayesian_stockout_prob > 0.60             |
| 15       | BAYESIAN       | DTO           | P(stockout in 14d) = 0.31. Redistribution effective       | bayesian_stockout_prob < 0.35             |

### SC-08 — Full network recovery (all networks)

| **Tick** | **Alert type**    | **Recipient**    | **Message summary**                                          | **Triggered by**                                      |
| -------- | ----------------- | ---------------- | ------------------------------------------------------------ | ----------------------------------------------------- |
| 5        | RECOMMENDATION    | All DTOs         | Recovery interventions activated across all 5 networks       | scenario start                                        |
| 15       | BAYESIAN          | Programme Manager | NET-D risk resolving: cascade_dropout_risk falling           | cascade_dropout_risk < 0.40 (NET-D)                  |
| 25       | DTO ADVISORY      | Programme Manager | NET-A and NET-B returned to green                            | status = ok for NET-A hub AND NET-B hub              |
| 35       | DTO ADVISORY      | Programme Manager | Full recovery complete. Impact metrics available in Tab 4    | global_tick = max_ticks                              |

## 6.3 Scenario configuration schema (YAML)

```yaml
scenarios:
  SC-01:
    name: "Network bottleneck"
    primary_network: NET-A
    max_ticks: 25
    affected_facilities: [DHC-A, TL1-A]
    per_tick_deltas:
      DHC-A:
        patients_queued: +1.8
        tat_hours: +0.6
        cascade_dropout_risk: +0.04
    shap_weights:              # per-field weight for SHAP stub — see §7
      patients_queued: 0.45
      tat_hours: 0.35
      cascade_dropout_risk: 0.20
    reroutes:
      - [MC2-A, TL2-A]
      - [CHC2-A, TL2-A]
    alerts:
      - tick: 4
        type: critical
        recipient: lab_supervisor
        facility: DHC-A
        msg: "DHC queue critical: {patients_queued:.0f} patients, TAT {tat_hours:.0f}h"
```

**Alert message interpolation:** `msg` strings are interpolated using `str.format_map()` against `FacilityState.__dict__` of the facility named in the `facility` field. Missing keys render as the literal key name in square brackets (e.g. `[unknown_field]`). A `safe_format(msg, facility_state)` helper in `core/models.py` handles this for all alert renderers.

# 7\. AI Model Layer

The simulation implements lightweight stubs for each of DiagNet's AI model layers. Each stub produces outputs structurally identical to the production model, enabling the dashboard and alert pipeline to be built without the full statistical machinery.

| **Model**                         | **Production algorithm**                                 | **Simulation stub**                                                                                                                         | **Output**                                                               | **SHAP display**                                         |
| --------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------- |
| B1 - Bayesian stockout forecaster | brms hierarchical negative-binomial + Stan MCMC          | scipy.stats.nbinom parameterised from NTEP district means; partial pooling approximated by shrinking sparse facilities toward district mean | P(stock ≤ 0 in 14 days) posterior scalar per facility ∈ [0.20, 0.95]    | Top 2 SHAP contributors as ±bar in tooltip               |
| B2 - Cascade dropout Bayes net    | bnlearn DAG + belief propagation                         | Lookup table of posterior probabilities indexed by observed evidence tuple                                                                  | Probability distribution over failure modes per episode ∈ [0.10, 0.90]  | Plain-language explanation from top-2 contributors       |
| M1 - Isolation Forest             | solitude::isolation_forest() on tabular episode features | Z-score on composite anomaly index with randomised noise                                                                                    | Anomaly score ∈ [0.30, 0.95] per episode; threshold 0.75                 | Feature contributions as horizontal bar chart            |
| M2 - Bottleneck (graph analytics) | igraph::betweenness() + igraph::page_rank()              | networkx.betweenness_centrality() + networkx.pagerank()                                                                                     | betweenness_score + pagerank_score + composite bottleneck_score per node | Score breakdown in facility detail panel                 |
| M3 - GCN facility embeddings      | torch + torch_geometric GCN                              | **v2 placeholder — not implemented in v1.** No embeddings computed in v1.                                                                   | n/a for v1                                                               | Not shown                                                |
| M4 - Optimal referral router      | igraph::distances() Dijkstra + Q-table RL                | networkx.dijkstra_path() with composite edge weight (travel_time + tat_penalty); Q-table pre-loaded from YAML lookup. **No M3 dependency.** | Ordered candidate facilities + estimated TAT per route                   | Route shown as blue dashed edge + cost breakdown tooltip |

**SHAP explainability — mandatory on every alert**

Every alert card must display a SHAP decomposition. In the simulation, SHAP values are computed from the scenario's `shap_weights` YAML field using the following algorithm:

1. For each field `f` with a non-zero `per_tick_delta` in the scenario YAML, compute `shap_f = per_tick_delta[f] × shap_weights[f]`.
2. Baseline = the facility's field value at tick 0 (from `data_generator.py` initial state).
3. Sort contributions by `|shap_f|` descending; display the top 5 in the waterfall (Tab 3) and top 2 in the alert card.

**Worked example — SC-01, tick 4, DHC-A:**

| Field | per_tick_delta | shap_weight | shap_f |
|---|---|---|---|
| patients_queued | +1.8 × 4 ticks = +7.2 | 0.45 | +3.24 |
| tat_hours | +0.6 × 4 = +2.4 | 0.35 | +0.84 |
| cascade_dropout_risk | +0.04 × 4 = +0.16 | 0.20 | +0.032 |

Alert card displays: "↑ Queue load (+3.24) · ↑ TAT (+0.84)". Waterfall in Tab 3 shows all 3 bars.

All SHAP displays carry the label **"Approximate · simulation mode"** to distinguish from production fastshap output.

# 8\. Dashboard Specification

## 8.1 Page layout — four-tab structure

| **Tab** | **Name**           | **Primary audience**      | **Contents**                                                                                         |
| ------- | ------------------ | ------------------------- | ---------------------------------------------------------------------------------------------------- |
| Tab 1   | Network Map        | All personas              | Plotly network graph, facility hover tooltips, alert panel, metrics bar                              |
| Tab 2   | Multi-Hub Overview | Programme Manager, DTO    | 5-network side-by-side mini-maps, inter-network flows, system-wide heatmap, cross-network alert feed |
| Tab 3   | Facility Detail    | Lab Supervisor, Clinician | Selected facility deep-dive: time-series charts, SHAP waterfall, alert history, recommended actions  |
| Tab 4   | Analytics & Export | Data team, DTO            | Tick history table, scenario comparison chart, Excel/PNG export, configuration viewer                |

## 8.2 Persistent top bar

- **Network selector** — dropdown to switch between NET-A through NET-E (or 'All networks' for Tab 2).
- **Scenario selector** — dropdown listing all 8 scenarios.
- **Run / Pause / Reset buttons** — Run starts the simulation loop; Pause freezes at the current tick; Reset clears simulation state (current_tick, active_alerts, active_reroutes) but preserves completed scenario snapshots in `st.session_state.scenario_snapshots[scenario_id]` for export. The simulation loop halts (`is_running = False`) before reset executes. The selected facility in Tab 3 is cleared on reset.
- **Speed slider** — 0.5× to 4×; controls only the `sleep_interval_s` between `st.rerun()` calls. Per-tick delta magnitudes are invariant to speed setting.
- **Tick counter** — current tick / max ticks, displayed as a progress bar.
- **Global alert badge** — count of active alerts across all networks, colour-coded by worst severity.

## 8.3 Tab 1 — Network Map

### Node encoding

- Size encodes tier: Hub = 30px, Truenat = 22px, Microscopy = 16px, CHC = 12px.
- Colour encodes status: green (#22c55e) = ok, amber (#f59e0b) = warning, red (#ef4444) = critical, grey = offline.
- Critical nodes display a static outer ring at 1.5× node radius in the critical colour (#ef4444) with 0.4 opacity, rendered as a second Plotly scatter trace behind the node. No animation in v1.

### Edge encoding

- Green solid = healthy link. Amber solid = one endpoint at-risk. Red dashed = one endpoint critical.
- Blue dashed = active reroute recommendation (appears at tick ≥ 6 when scenario is active).

### Alert panel

- Fixed-height scrollable panel (right column, 220px wide) showing the **14 most recent** AlertRecords from `NetworkState.alerts` for the currently selected network.
- Alerts persist for the lifetime of the current scenario run (they do not expire per tick).
- Same-tick duplicate alerts (same `type` + same `facility_id`) are deduplicated before insertion.
- At tick 0 before the simulation runs, the panel displays: *"No alerts — simulation not started."*
- Three visual styles: CRITICAL (red), DTO ADVISORY (amber), BAYESIAN/RECOMMENDATION (blue).
- Each card: alert type badge, tick timestamp, message text, 2-line SHAP explanation.

### Metrics bar

- 5 metric cards: Critical sites count, At-risk sites count, Total patients queued, Low-cartridge sites count, Average cascade dropout risk %.
- Metric values display delta vs. previous tick using `st.metric()` delta parameter.

## 8.4 Tab 2 — Multi-Hub Overview

- 5-column grid of mini network maps (~200×200px each), one per network. Mini-maps render from `st.session_state.graph_cache[network_id][tick]` — not recomputed per rerun.
- Inter-network flow arrows: curved lines between network bounding boxes; colour = flow status.
- System-wide heatmap: bar chart of `composite_bottleneck_score` for all 59 nodes, sorted descending.
- Global alert feed: combined alert stream from all 5 networks with network ID badge on each card.
- **'Run SC-08' button**: launches SC-08 (Full network recovery, all 5 networks). SC-04 is accessible via the scenario dropdown and always runs on NET-D as primary network.

## 8.5 Tab 3 — Facility Detail

**Selecting a facility:** Clicking a node on the Tab 1 network map writes `st.session_state.selected_facility = facility_id` via the Plotly `plotly_click` callback captured from `st.plotly_chart()`. Tab 3 reads `st.session_state.selected_facility` and renders the detail view for that facility. If no facility is selected, Tab 3 displays: *"Click any node on the Network Map to open facility detail."*

Tab-switching is not required: Tab 3 renders the selected facility's content regardless of which tab is active, so the user switches to Tab 3 manually after clicking a node. No programmatic tab-switch API is used.

- **4 Plotly line charts:** patients queued, cartridges, TAT, cascade dropout risk — full tick history with threshold lines.
- **SHAP waterfall:** top-5 feature contributions to current risk score as horizontal bar chart (labelled "Approximate · simulation mode").
- **Recommended actions:** 3 pre-authored action strings sourced from `scenario YAML` under `recommended_actions[facility_id][tick_range]`. Displayed verbatim; not dynamically generated.
- **Alert history:** scrollable list of all alerts fired for this facility in the current scenario run.

## 8.6 Tab 4 — Analytics & Export

- **Tick history table:** full DataFrame of all FacilityState values at every tick, filterable by facility and metric. Exportable to Excel via openpyxl.
- **Scenario comparison:** Post-hoc only. After any scenario completes, its tick history is saved to `st.session_state.scenario_snapshots[scenario_id]`. Tab 4 allows selecting any two saved snapshots and one metric; renders a dual-line Plotly chart showing metric divergence. No simultaneous dual-run is required or supported.
- **Configuration viewer:** read-only display of active YAML configs with a download button for offline editing. Write-back is out of scope for v1 (see §1.2).
- **Screenshot:** exports the active Plotly network map figure (Tab 1 graph only, not the full dashboard) to a high-resolution PNG using `plotly.io.write_image(fig, path, engine='kaleido', width=1920, height=1080)`. The simulation must be paused before screenshot is triggered. kaleido must be installed and bundled for offline operation (see §3.3).

# 9\. Non-Functional Requirements

| **Requirement**          | **Target**                                                                                       | **Measurement**                                              |
| ------------------------ | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| Tick render latency      | < 400 ms from state update to graph rerender at max speed (4×)                                   | st.session_state.perf_log                                    |
| Simultaneous networks    | All 5 networks renderable on Tab 2 without perceptible lag (graph metrics cached per tick)       | FPS counter displayed in debug mode                          |
| State serialisation      | Full tick history (35 ticks × 59 facilities × 17 fields) serialisable to JSON in < 500 ms        | Benchmarked in tests/test_export.py                          |
| Configuration validation | Invalid YAML must raise a readable Pydantic error, not a Python traceback                        | Test suite covers 10 malformed configs                       |
| Reproducibility          | Same scenario with same random seed must produce identical tick sequence                         | Verified in tests/test_simulation.py                         |
| Accessibility            | Alert cards must meet WCAG AA colour contrast; Plotly figures use both colour and shape encoding | See colour spec below; manual audit pre-submission           |
| Offline operation        | App must run fully offline; kaleido bundled for screenshot export                                | No CDN dependencies; all assets bundled                      |
| Browser compatibility    | Chrome ≥ 120, Firefox ≥ 121, Safari ≥ 17                                                         | Manual QA checklist before submission                        |

**WCAG AA colour specification for alert cards:**

| **Alert type**     | **Background** | **Text colour** | **Contrast ratio** | **Passes AA** |
| ------------------ | -------------- | --------------- | ------------------ | ------------- |
| CRITICAL           | #dc2626        | #ffffff         | 4.5:1              | Yes           |
| DTO ADVISORY       | #fef3c7        | #92400e         | 7.3:1              | Yes           |
| BAYESIAN / RECOMMENDATION | #eff6ff | #1e40af        | 5.9:1              | Yes           |

# 10\. Implementation Plan

## 10.1 Three-week development timeline

| **Week**       | **Milestone**                                        | **Modules delivered**                                                       | **Owner**            | **Acceptance criteria**                                                                               |
| -------------- | ---------------------------------------------------- | --------------------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------- |
| Week 1 1-2 Jun | Foundation: data model + graph engine + config       | core/models.py, core/data_generator.py, core/graph.py, config/networks.yaml | Mihir + Dr Prashanth | All 5 networks load from YAML; NetworkX graph builds; betweenness + PageRank compute for all 59 nodes; GlobalState constructs without error |
| Week 2 3-5 Jun | Simulation engine + alert pipeline + Tab 1           | core/simulation.py, viz/alerts.py, viz/network_map.py, app.py (Tab 1)       | Mihir                | SC-01, SC-02, SC-03 run on their primary networks; all alerts fire at correct ticks per §6.2; SHAP stub displays with correct signs and magnitudes |
| Week 3 6-9 Jun | Multi-hub UI + remaining scenarios + export + polish | app.py (Tabs 2-4), SC-04-SC-08, config/scenarios.yaml, export, screenshot   | Full team            | All 8 scenarios run to max_ticks; Tab 2 renders 5 networks simultaneously; Excel export produces non-empty file; screenshot exports valid PNG |

## 10.2 Module build order

- config/networks.yaml + config/scenarios.yaml (no dependencies)
- core/models.py (pure dataclasses)
- core/data_generator.py (depends on: models.py, networks.yaml)
- core/graph.py (depends on: models.py)
- core/simulation.py (depends on: models.py, graph.py, scenarios.yaml)
- viz/network_map.py (depends on: models.py)
- viz/alerts.py (depends on: models.py)
- app.py (depends on: all of the above)

## 10.3 Testing strategy

- Unit tests (pytest): core/models.py, core/data_generator.py, core/graph.py, core/simulation.py — 80% line coverage target.
- Scenario regression tests: each scenario run to completion with fixed seed; output compared to golden JSON fixture.
- Visual QA: screenshot of each tab at ticks 0, 7, 15, 25, 30, 35 compared against reference images.
- Performance test: all 5 networks simulated simultaneously for 35 ticks; total wall time < 60 seconds.

# 11\. Configuration Reference

## 11.1 networks.yaml structure

All facility definitions, baseline metrics, links, and display properties are defined here. Domain experts can adjust thresholds and baseline values without touching Python code.

```yaml
networks:
  NET-A:
    display_name: "District Hospital Chandrapur"
    hub_type: CBNAAT
    facilities:
      DHC-A:
        display_name: "District Hospital Chandrapur"
        type: hub
        x: 0.50     # normalised canvas position 0-1
        y: 0.88
        baseline:
          patients_queued: 42
          cartridges: 120
          daily_consumption: 8    # cartridges per day at baseline
          tat_hours: 18
          hr_on_shift: 8
          machines: 3
          modules: 6
          samples_per_module_per_day: 28
        thresholds:
          patients_queued: { warn: 35, critical: 55 }
          cartridges: { warn: 25, critical: 10 }
          tat_hours: { warn: 24, critical: 36 }
    links:
      - [CHC1-A, MC1-A, 55]   # [from, to, travel_time_minutes]
      - [MC1-A, TL1-A, 34]
      - [TL1-A, DHC-A, 52]

inter_network_links:
  - source: NET-D
    target: NET-A
    source_facility: DHC-D
    target_facility: DHC-A
    travel_time_min: 240
    flow_type: overflow
```

## 11.2 Alert threshold customisation

Alert thresholds are defined per-facility in networks.yaml. The simulation engine reads these at startup and applies them without code changes. This allows domain experts to calibrate thresholds to local district norms.

# 12\. Open Questions & Risks

| **#** | **Risk / open question**                                                                                   | **Likelihood** | **Impact**         | **Mitigation**                                                                                                             |
| ----- | ---------------------------------------------------------------------------------------------------------- | -------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| R-01  | Streamlit rerun loop introduces perceptible lag at 4× speed with all 5 networks rendering simultaneously   | Medium         | High               | Graph metrics cached in st.session_state.graph_cache per tick; Tab 2 renders from cache                                    |
| R-02  | YAML config grows unwieldy at 59 nodes                                                                     | Low            | Medium             | Split into per-network YAML files; auto-validate on load with Pydantic                                                     |
| R-03  | SHAP stub values are not statistically rigorous; reviewers may question methodology                        | Medium         | High               | All SHAP displays labelled "Approximate · simulation mode"; production path to fastshap documented                          |
| R-04  | brms/Stan rpy2 integration deferred                                                                        | Resolved       | n/a                | v1 ships scipy stub only; rpy2 removed from v1 stack                                                                       |
| R-05  | Inter-network overflow requires state synchronisation across NetworkState objects                          | Resolved       | n/a                | GlobalState §5.4 specifies the contract; synchronous global tick; apply_overflow() called after all per-network deltas      |
| R-06  | Demo environment may have restricted internet access                                                       | Low            | High               | Bundle Plotly JS locally; bundle kaleido; test in offline mode before submission                                           |
| R-07  | Non-technical audience may find the 59-node network map overwhelming                                       | Medium         | Medium             | Default view shows active scenario network only; 'All networks' toggle is opt-in; CHC nodes are small (12px) and clustered |
| R-08  | kaleido unavailable on demo machine                                                                        | Low            | High               | Bundle kaleido in requirements.txt; test screenshot on target demo hardware; fallback: instruct user to use browser print-to-PDF |

# 13\. Glossary

| **Term**                    | **Definition**                                                                                                                                           |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bayesian hierarchical model | A statistical model that shares information across groups using a common prior distribution. Produces full posterior distributions, not point estimates. |
| Betweenness centrality      | Graph metric: fraction of all shortest paths between node-pairs passing through a given node. High = structural chokepoint.                              |
| CBNAAT                      | Cartridge-Based Nucleic Acid Amplification Test. GeneXpert is the dominant CBNAAT platform in NTEP.                                                      |
| Cascade dropout             | A patient who enters the TB diagnostic cascade but does not complete it.                                                                                 |
| CHC                         | Community Health Centre. First formal health facility in rural India.                                                                                    |
| CHW                         | Community Health Worker. Frontline health worker who escorts patients through the diagnostic cascade.                                                    |
| DAG                         | Directed Acyclic Graph. Encodes causal relationships between diagnostic failure modes in Model B2.                                                       |
| DHIS2                       | District Health Information System version 2. Open-source platform for aggregating facility-level NTEP reports.                                          |
| DST                         | Drug Susceptibility Testing. Determines TB drug resistance. Requires culture, adding 6-8 weeks.                                                          |
| DTO                         | District TB Officer. Primary operational decision-maker for TB diagnostics in a district.                                                                |
| Federated learning          | ML architecture where training occurs locally at each district node; only gradients, not patient data, are shared.                                       |
| GCN                         | Graph Convolutional Network. Learns representations from both node features and graph structure. Planned for v2.                                          |
| GeneXpert                   | CBNAAT machine by Cepheid. Each machine has 1-4 modules; each module processes one cartridge at a time.                                                  |
| GlobalState                 | Top-level simulation state object holding all 5 NetworkStates and coordinating inter-network overflow. See §5.4.                                         |
| HMIS                        | Health Management Information System. Government databases storing patient visit records and test results.                                               |
| Isolation Forest            | Anomaly detection algorithm that isolates outliers by measuring how few random splits separate a point.                                                  |
| LIS                         | Laboratory Information System. Tracks test orders, specimen handling, results, and turnaround times.                                                     |
| LSTM                        | Long Short-Term Memory recurrent network. Used to model test-ordering sequences in DiagNet.                                                              |
| NIKSHAY                     | India's national TB patient management system operated by the Central TB Division.                                                                       |
| node2vec                    | Graph embedding technique that uses biased random walks on the graph to produce vector representations of nodes. Used as a lower-complexity approximation of full GCN training. Planned for v2 (M3). |
| NTEP                        | National TB Elimination Programme. India's government programme targeting TB elimination by 2025/2030.                                                   |
| OSRM                        | Open Source Routing Machine. Road-network routing engine built on OpenStreetMap data.                                                                    |
| PageRank                    | Graph metric identifying 'sink' facilities absorbing disproportionate referral share.                                                                    |
| Q-learning                  | Model-free RL algorithm. Q-table maps (state, action) pairs to expected rewards; updated with each real outcome.                                         |
| SHAP                        | SHapley Additive exPlanations. Assigns each feature a contribution score for a specific prediction.                                                      |
| TAT                         | Turnaround Time. Elapsed time between specimen collection and result delivery.                                                                           |
| Truenat                     | Portable molecular TB testing device by Molbio. Requires Truenat chips; operates without stable electricity.                                             |

# A\. Assumptions Index

| **#** | **Assumption**                                                                                                  | **Owner**       | **Validation plan**                                                              |
| ----- | --------------------------------------------------------------------------------------------------------------- | --------------- | -------------------------------------------------------------------------------- |
| A-01  | Synthetic baseline states (59 nodes, field values in §5.1) are clinically plausible enough for domain expert reviewers at the June presentation | Dr Lakshmi, Carel | Review baseline YAML values with domain experts before Week 3 demo rehearsal |
| A-02  | Demo runs on a single laptop (not a server); performance NFRs (< 400ms render, < 500ms serialisation) are targeted at laptop-class hardware | Dr Aswath | Run performance test on the target demo machine in Week 3 |
| A-03  | SHAP approximation from per_tick_deltas × shap_weights is acceptable to technical reviewers when labelled "Approximate · simulation mode" | Mihir | Validate with one technical reviewer before submission |
| A-04  | v2 (brms/Stan/rpy2, GCN/node2vec, federated learning) is out of scope for the June submission and will not be scoped in without explicit re-scoping by the project lead | Dr Aswath | Confirmed in §1.2 Non-Goals |

---

**DiagNet** · Diagnostic Network Intelligence for TB Care

_PRD v1.1 · PATH South Asia Digital Health · Hackathon 2026 · Updated 2026-06-04_
