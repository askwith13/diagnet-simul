# Adversarial Review — DiagNet Simulation PRD

## Summary

The PRD establishes a coherent domain model and a workable architecture, but contains at least six implementation-blocking gaps that will force developers to make incompatible guesses during the sprint: the GlobalState for inter-network overflow is mentioned as a mitigation but never specified as a data contract, the node-click → Tab 3 navigation pattern is technically impossible in standard Streamlit and no workaround is given, the SHAP stub approximation is named but its computation algorithm is absent, and SC-08 "Simulate all" has no specified orchestration protocol. With today being 2026-06-04 and the deadline 9–10 June, the team has at most 5 coding days — the multi-hub Tab 2, all 8 scenarios, export, screenshot, and Tab 3 are Week 3 scope that realistically requires two weeks, not four days.

---

## Findings

### CRITICAL — GlobalState inter-network data contract is missing from the data model

**Location:** §4.3 Inter-network connections; §12 R-05 mitigation; §5.3 NetworkState

**Problem:** Section 4.3 establishes three inter-network links (NET-A↔NET-C, NET-B↔NET-D, NET-D→NET-A) and R-05 says "Introduce a GlobalState container holding all 5 NetworkStates with overflow delta propagation." However, GlobalState appears nowhere in §5 (the data model section). There is no definition of: what fields GlobalState contains, how overflow_deltas are structured, what the interface between simulation.py and GlobalState is, who owns the cross-network tick synchronisation, or how conflicting ticks are resolved when NET-D is on tick 22 and NET-A is on tick 18. Two developers will independently invent different schemas and produce incompatible modules.

**Impact:** SC-04 (cascade failure + inter-network) and SC-08 (all networks) are completely blocked until this is resolved. These are the two scenarios that provide the highest-value demo moments (the "key multi-hub insight" the PRD itself calls out). If each developer builds their own GlobalState, integration will cost a full day of refactoring.

**Fix:** Add a §5.4 GlobalState specification to the PRD. Minimum fields: `network_states: Dict[str, NetworkState]`, `inter_network_flows: List[InterNetworkFlow]` (typed dataclass with `source_net`, `target_net`, `patient_count`, `tick`), `global_tick: int`, `overflow_pending: Dict[str, float]`. Specify the tick-synchronisation rule: all networks advance together (synchronous global tick) or independently (async with a merge step). Specify who calls GlobalState.apply_overflow().

---

### CRITICAL — Node click → Tab 3 navigation has no specified implementation path

**Location:** §8.5 Tab 3; §8.3 Tab 1 alert panel

**Problem:** "Accessed by clicking any node on the network map." Streamlit does not expose a native callback that lets a Plotly `clickData` event change the active tab. `st.tabs()` in Streamlit ≥ 1.35 has no programmatic tab-switching API — tab selection is a DOM event that Streamlit does not route back to Python. The standard workaround (a `st.session_state` flag + a JS `window.parent.postMessage` injection via `st.components.v1.html`) is non-trivial, undocumented in the PRD, and fragile across Streamlit minor versions. Without a specified workaround, one developer will use `st.experimental_set_query_params` (deprecated), another will use a custom component, and a third will downgrade to a sidebar selectbox, producing three incompatible UI behaviours.

**Impact:** Tab 3 is the SHAP explainability showcase — the single feature the Funder/Reviewer persona needs to see. If node click is broken or replaced with a workaround that doesn't feel interactive, the highest-value demo moment fails.

**Fix:** The PRD must specify the exact workaround. Recommended: capture `plotly_click` event from `st.plotly_chart(use_container_width=True)` into `st.session_state.selected_facility`; render Tab 3 content conditionally inside the same page below the tab bar using `st.expander` or a dedicated `st.container` that expands on click — this avoids the tab-switching problem entirely. Alternatively, accept that Tab 3 is a separate view reached via a selectbox, and remove the "clicking any node" language.

---

### CRITICAL — SHAP stub computation algorithm is not specified

**Location:** §7 AI Model Layer; §8.3 Alert panel; §8.5 Tab 3

**Problem:** The PRD states "SHAP values are approximated from the per_tick_deltas in the scenario YAML." This is a name, not an algorithm. There is no specification of: what the base value (expected value) is, how per_tick_deltas map to SHAP feature importances, whether the sign of a delta becomes the sign of the contribution, how the magnitudes are normalised to sum to the predicted risk score, or what happens when a facility has no active per_tick_delta (i.e., facilities not in `affected_facilities`). The SHAP waterfall chart requires concrete positive/negative bars with numeric values — a developer cannot implement this from "approximated from per_tick_deltas."

**Impact:** The SHAP waterfall (Tab 3) and the 2-bar SHAP chart in every alert card are mandatory per §7 ("SHAP explainability — mandatory on every alert"). If each developer invents their own mapping, the outputs will be inconsistent across models B1, B2, M1, M2, and across scenarios. The requirement that SHAP is "mandatory on every alert" means this gap blocks every alert card's implementation.

**Fix:** Specify the algorithm explicitly. A minimal workable spec: for each field `f` with a non-zero per_tick_delta `d_f`, `shap_f = d_f × weight_f` where `weight_f` is a per-field constant defined in the YAML (or a hardcoded table). The waterfall baseline = facility's value at tick 0. Contributions are sorted by |shap_f| descending; top 5 displayed. Include a worked example for SC-01 tick 4 showing numeric inputs and outputs.

---

### CRITICAL — SC-08 "Simulate all" orchestration is unspecified

**Location:** §6.1 SC-08; §8.4 Tab 2 "Simulate all" button

**Problem:** SC-08 is "Full network recovery: Post-crisis: interventions applied → all networks return to green → impact metrics" with max_ticks 35. The scenario catalogue assigns it `primary_network: All 5 networks`. However: (1) there is no definition of what state all 5 networks are in at SC-08 start — are they in the post-SC-04 crisis state, or do they each get reset to their own baseline? (2) the YAML schema in §6.3 only shows single-network delta structures — there is no multi-network delta schema. (3) "impact metrics" at completion is mentioned but not defined — what metrics, computed how, displayed where? (4) the `primary_network` field in the YAML schema has no documented semantics for the value "All 5 networks." (5) the "Simulate all" button on Tab 2 is described as "runs SC-04" in one place and "Full network recovery" (SC-08) in another — these are different scenarios.

**Impact:** SC-08 is the final climactic demo moment. It is also the most complex scenario to implement. Without a spec it cannot be built in the sprint.

**Fix:** Define SC-08's start state explicitly (recommended: networks enter pre-loaded "post-crisis" baseline states defined in YAML, not derived from a prior scenario run — avoids state dependency). Add a multi-network delta schema to §6.3. Define "impact metrics" as a specific set of computed aggregates (e.g., mean composite_bottleneck_score across all networks, total patients_queued reduction, number of facilities returning to green). Clarify the Tab 2 button: it should be labelled "Run SC-08" not "Simulate all." Resolve the discrepancy with SC-04.

---

### HIGH — Speed slider effect on simulation deltas is underspecified

**Location:** §8.2 Persistent top bar; §6.3 Scenario YAML schema

**Problem:** The speed slider is described as controlling "both tick rate and per-tick state delta magnitude." This is ambiguous in two ways. First, "delta magnitude" — does the speed multiplier scale the `per_tick_deltas` linearly (4× speed = 4× delta per tick) or does it only change the wall-clock interval between ticks (faster animation, same cumulative state change)? These produce dramatically different simulation outcomes. At 4× if deltas scale, a 25-tick scenario converges in ~6 ticks; if they don't scale, the scenario takes the same number of ticks at higher animation speed. Second, the YAML schema uses absolute delta values (`patients_queued: +1.8`). If speed scales deltas, the YAML must store a base delta and the engine scales it — but this is not stated. The NFR says "< 400 ms tick render at 4×" which implies the ticks still happen, suggesting speed = animation rate only.

**Impact:** Developer A builds a speed multiplier that scales deltas (producing accurate "compressed time" semantics), Developer B builds it as a pure animation rate change. The two implementations produce completely different scenario progressions and alert timings — alert at tick 4 fires at wall-clock second 2 vs. 8. Integration will be a conflict.

**Fix:** Specify explicitly: speed slider controls only the `sleep_interval_s` between `st.rerun()` calls. Per-tick deltas are not scaled by speed. Add one sentence to §8.2: "Speed controls animation rate only; scenario delta magnitudes are invariant to speed setting."

---

### HIGH — effective_capacity formula has an ambiguous unit collision

**Location:** §5.2 Derived metrics

**Problem:** `effective_capacity = min(cartridges / daily_consumption, modules × max_samples_per_module)`. The formula has two unresolved references: `daily_consumption` is not a field in FacilityState (§5.1 lists 16 fields — `daily_consumption` is not among them), and `max_samples_per_module` is not a field in FacilityState either (the field is `samples_per_module_per_day`, which is an observed rate, not a maximum capacity). The left term `cartridges / daily_consumption` produces days-of-stock-remaining. The right term `modules × max_samples_per_module` produces samples/day capacity. These are different units: one is days, one is samples/day. `min()` across different units is meaningless. A developer implementing this formula will either (a) produce a dimensionally incorrect metric or (b) invent their own interpretation.

**Impact:** `effective_capacity` feeds `predicted_stockout_day` and the tooltip. A wrong formula gives wrong stockout day predictions, which undermines the Bayesian forecasting demo.

**Fix:** Either (a) add `daily_consumption` and `max_samples_per_module` as explicit FacilityState fields or YAML baseline fields, or (b) rewrite the formula with consistent units: `effective_capacity_days = cartridges / samples_per_module_per_day` (days until cartridges exhausted at current consumption rate). The second right-hand term should be removed or renamed to `throughput_capacity_samples_per_day = modules × samples_per_module_per_day` as a separate metric.

---

### HIGH — Screenshot mode scope is undefined

**Location:** §8.6 Tab 4 "Screenshot mode"

**Problem:** "Renders current network map to high-resolution PNG (1920×1080) for slide embedding." Three ambiguities: (1) "current network map" — is this only the Plotly figure from Tab 1, or the full 4-tab dashboard? (2) The full dashboard cannot be rendered to PNG by `plotly.io.write_image()` — that API only exports a single Plotly figure. Capturing a full Streamlit dashboard requires a headless browser (Playwright/Selenium) or a server-side screenshot tool, which violates the offline + zero-infrastructure deployment constraint. (3) "current" — does it capture the state at the moment the button is clicked, or does the user first pause, then screenshot?

**Impact:** If a developer attempts to implement full-dashboard PNG export using `plotly.io.write_image()` it will only capture one chart. If they reach for Playwright, they introduce a heavy dependency that may not be installable offline. This feature will either be silently downgraded or block a day of debugging.

**Fix:** Narrow the scope explicitly: "Screenshot exports only the active Plotly network map figure (Tab 1 or the selected mini-map from Tab 2) using `plotly.io.write_image()` with `engine='kaleido'`." Add `kaleido` to the dependency list. Document that kaleido must be bundled for offline operation. Specify that the simulation must be paused before screenshot is triggered (no ambiguous "current" state).

---

### HIGH — Scenario YAML schema is incomplete for alert interpolation

**Location:** §6.3 Scenario configuration schema

**Problem:** The example alert message `msg: "DHC queue critical: {patients_queued:.0f} patients"` uses f-string-style interpolation, but the YAML is a static string. The PRD does not specify: (a) which object's namespace is used for interpolation (the FacilityState of which facility? the first affected_facility? the recipient facility?), (b) what happens if the interpolation key doesn't exist on FacilityState at runtime (KeyError vs. silent fallback), (c) whether nested attribute access is supported (e.g., `{facility.tat_hours:.1f}`). Two developers will implement different interpolation engines.

**Impact:** Alert messages are a primary demo output — they must be correct and readable. A runtime KeyError in an alert interpolation during a live demo is a catastrophic failure mode.

**Fix:** Specify the interpolation context explicitly: "Message strings are interpolated using Python `str.format_map()` against the FacilityState.__dict__ of the first facility in `affected_facilities`. Missing keys render as the literal key name in brackets." Provide a safe-format helper in `core/models.py` so every module uses the same renderer.

---

### HIGH — Tick history serialisation size vs. 500ms budget is not validated

**Location:** §9 NFRs; §5.3 NetworkState tick_history

**Problem:** The NFR states "Full tick history (25 ticks × 59 facilities × 16 fields) serialisable to JSON in < 500 ms." The rough data volume: 25 × 59 × 16 = 23,600 float/int values. With field names, this is ~1.5–2 MB of JSON — well within 500ms for `json.dumps`. However, `tick_history: List[Dict]` is stored inside each NetworkState object. When all 5 networks run SC-08 (35 ticks), `tick_history` grows to 35 × 59 × 16 × 5 = 164,500 values across all networks, and the immutable tick state constraint means each NetworkState in tick_history also contains its own nested tick_history from previous ticks — this is an O(n²) space blowup for tick_history-within-tick_history. If tick_history naively includes the full NetworkState (which includes tick_history), serialisation will hit a recursive structure.

**Impact:** Either a RecursionError during JSON serialisation, or a multi-second export time on SC-08. Either kills the Tab 4 export demo.

**Fix:** Specify that `tick_history` stores a serialised-flat snapshot of FacilityState values only (not nested NetworkState objects). Add to §5.3: "Each entry in tick_history is a flat dict: `{tick: int, facility_id: str, **facility_state_fields}`. The tick_history list is excluded from NetworkState serialisation snapshots to prevent recursive growth."

---

### MEDIUM — Pulsing ring animation is not implementable in static Plotly

**Location:** §8.3 Node encoding

**Problem:** "Pulsing ring animation on critical nodes (opacity oscillates 0.15–0.70 at ~1.2 Hz)." Plotly Graph Objects does not support per-frame opacity oscillation natively. Plotly's animation API (`frames`) requires the entire figure to be rebuilt per frame, which at 1.2 Hz means ~0.83-second rebuilds conflicting with the 400ms tick render budget. The Streamlit `st.rerun()` loop can approximate this if the rerun interval is < 830ms, but the tick rate at 4× speed will be much faster than 830ms, and the animation would be tick-locked, not time-locked. This is a known Streamlit-Plotly limitation with no clean solution.

**Impact:** Developer will either (a) skip the animation silently, (b) use a CSS `@keyframes` injection via `st.markdown` (fragile, browser-dependent, may break offline), or (c) waste significant time before abandoning the feature. For a hackathon demo, animated pulse rings are a "nice to have" that could become a sprint time sink.

**Fix:** Downgrade the requirement: "Critical nodes display a static outer ring at 1.5× node radius in the critical colour with 0.4 opacity. Pulsing animation is deferred to v2.0." This removes ambiguity about implementation approach.

---

### MEDIUM — Scenario comparison (Tab 4) requires two simultaneous scenario runs with no state isolation spec

**Location:** §8.6 Tab 4

**Problem:** "Select 2 scenarios and one metric; renders dual-line Plotly chart showing metric divergence." This requires storing the full tick_history of two separate scenario runs simultaneously. The PRD does not specify: (a) whether both scenarios must be run to completion before comparison is available (blocking) or whether they can be run concurrently (requiring two independent simulation state trees), (b) whether the comparison is cross-network (SC-01 on NET-A vs. SC-02 on NET-B) or same-network (SC-01 on NET-A vs. SC-06 on NET-A), (c) how `st.session_state` stores two independent tick_history streams without collision, (d) whether the "current run" is scenario A or B when the top bar controls are used. There is no data model for "scenario comparison state."

**Impact:** This feature will either be implemented as a post-hoc comparison (run scenario A, save output, run scenario B, compare) — which requires the user to complete two full simulation runs and remember to save — or as a simultaneous dual-run which requires significant additional session state scaffolding. The developer will have to invent the implementation from scratch.

**Fix:** Specify the flow: "Scenario comparison is post-hoc only. After any scenario completes, its tick_history is saved to `st.session_state.scenario_snapshots[scenario_id]`. Tab 4 comparison allows selecting any two saved snapshots. No simultaneous dual-run is required."

---

### MEDIUM — "14 most recent alerts" panel: alert persistence and deduplication rules absent

**Location:** §8.3 Alert panel

**Problem:** The alert panel shows "14 most recent alerts." The PRD does not specify: (a) whether alerts persist across ticks (an alert fired at tick 4 still shows at tick 25) or expire after N ticks, (b) whether the same alert can fire again if the condition re-triggers (deduplication), (c) whether the list is per-network (only alerts from the currently selected network) or global (all networks), (d) what happens at tick 0 before any alerts fire — is the panel empty or does it show placeholder text. For a 25-tick scenario with 4 alerts (SC-01 example), persistence of all prior alerts means the panel will never scroll. For SC-08 across 5 networks, 35 ticks × potential alerts per tick could produce hundreds of entries — the "14 most recent" cap becomes critical but is not defined clearly in terms of time-ordering when multiple networks fire simultaneously.

**Impact:** Two alert implementations: one that clears alerts on new tick, one that accumulates them. The visual output will look completely different. Cross-network tab: alerts from NET-D showing in NET-A's panel is a correctness bug, not just a cosmetic issue.

**Fix:** Add to §8.3: "The alert panel shows the 14 most recent AlertRecord objects from `NetworkState.alerts` for the currently selected network. Alerts persist for the lifetime of the current scenario run. Same-tick duplicate alerts (same type + same facility) are deduplicated. At tick 0 the panel displays 'No alerts — simulation not started.'"

---

### MEDIUM — "Simulate all" button appears to conflict with SC-04 assignment

**Location:** §8.4 Tab 2; §6.1 SC-08

**Problem:** §8.4 states: "'Simulate all' button: runs SC-04 (cascade failure + inter-network) spanning multiple networks." §6.1 defines SC-08 as "Full network recovery: All 5 networks." These are different scenarios. The button label "Simulate all" also implies "run all scenarios" or "run all networks" — neither SC-04 nor SC-08 fits that description precisely. SC-04 is primarily NET-D with overflow to NET-A; SC-08 is multi-network recovery. A developer reading §8.4 will implement "Simulate all = SC-04." A developer reading §6.1 will implement "Simulate all = SC-08." These produce different UI behaviours.

**Impact:** Wasted implementation work when the conflict is discovered during integration. The button is on Tab 2, which is Week 3 scope.

**Fix:** Decide and specify: "The 'Simulate all' button launches SC-08. SC-04 is accessible via the scenario dropdown and always runs on NET-D as primary network. SC-08 is the only scenario that runs all 5 networks simultaneously and is the only scenario accessible via the 'Simulate all' button."

---

### MEDIUM — node2vec approximation for M3 is computationally unspecified

**Location:** §7 AI Model Layer (M3)

**Problem:** M3 is described as "NetworkX node2vec approximation using random walks → 128-dim embedding per facility; input to M4." NetworkX does not include node2vec natively. The `node2vec` Python package exists but is not listed in the technology stack (§3.3). The PRD says "approximation using random walks" without specifying: the walk length, number of walks, p/q parameters, the embedding algorithm (Word2Vec on walk sequences?), how the 128 dimensions are consumed by M4 (Dijkstra + Q-table), and why M4 (which uses Dijkstra path-finding) would need 128-dim embeddings as input — Dijkstra operates on edge weights, not node embeddings. The "input to M4" claim appears architecturally inconsistent.

**Impact:** M3 is labelled "internal, not shown in demo" which reduces demo risk, but if M4 depends on M3's output and M3 is not implemented, M4 is broken. The dependency chain is: M3 output → M4 input → optimal route → Tab 1 blue dashed edge. If M4 silently falls back to plain Dijkstra, the Q-table claim is misleading.

**Fix:** Either (a) decouple M3 from M4: specify that M4 uses only Dijkstra with composite edge weights (travel_time + tat_penalty) and the Q-table is pre-loaded from a hardcoded YAML lookup — no M3 dependency; or (b) add `node2vec` to the dependency list and specify the walk parameters. Option (a) is the safer 5-day scope choice.

---

### LOW — YAML schema for inter-network links is absent

**Location:** §4.3 Inter-network connections; §11.1 networks.yaml structure

**Problem:** The networks.yaml structure in §11.1 shows intra-network links as `links: - [CHC1-A, MC1-A, 55]`. Inter-network connections (NET-A↔NET-C, NET-B↔NET-D, NET-D→NET-A) are described in prose but have no YAML representation. There is no schema for: where inter-network links live in the YAML (top-level `inter_network_links` key? Inside each network's definition?), what properties they carry (is travel_time meaningful across districts? what is the directionality encoding?), and how `core/graph.py` constructs a cross-network graph when each NetworkState only knows its own facilities.

**Impact:** The inter-network graph cannot be constructed from the YAML as specified. A developer will invent a schema, another will invent a different schema, and the GlobalState graph constructor will not agree with either.

**Fix:** Add a top-level `inter_network_links` key to §11.1 with example: `inter_network_links: - source: NET-D, target: NET-A, source_facility: DHC-D, target_facility: DHC-A, travel_time_min: 240, flow_type: overflow`.

---

### LOW — WCAG AA requirement for alert cards has no colour-contrast spec for the amber DTO ADVISORY colour

**Location:** §9 NFRs; §8.3 Alert panel

**Problem:** The alert panel uses three colour styles: CRITICAL (red #ef4444), DTO ADVISORY (amber #f59e0b), BAYESIAN (blue). WCAG AA requires a contrast ratio of at least 4.5:1 for normal text. Against a white background: #ef4444 (red) has a contrast ratio of ~4.0:1 — this fails WCAG AA for normal-weight text. #f59e0b (amber) has a contrast ratio of ~2.8:1 — this fails WCAG AA even for large text. The PRD specifies these colours in §8.3 for nodes but does not give the alert card text colour. If white text (#ffffff) is used on the amber badge, the contrast drops further to ~1.8:1.

**Impact:** The PRD explicitly lists "Alert cards must meet WCAG AA colour contrast" as an NFR. As specified, the colours will fail WCAG AA on submission. A manual audit pre-submission will catch this, but the fix (darkening the palette or using dark text on light backgrounds) may require reworking the entire colour system.

**Fix:** Add a colour specification table to §9 or §8.3: specify both the background and foreground text colour for each alert severity, and confirm the pair meets WCAG AA. Recommended: CRITICAL = red background #dc2626 with white text (4.5:1); DTO ADVISORY = amber background on white card with dark text #92400e (7.3:1); BAYESIAN = blue background #1d4ed8 with white text (5.9:1).

---

### LOW — Reset button behaviour during active run is underspecified

**Location:** §8.2 Persistent top bar

**Problem:** The PRD describes "Reset returns to initial state" but does not specify: (a) whether Reset during an active run immediately stops the simulation before resetting, or whether a running simulation can be reset mid-tick (risking partial state write), (b) whether tick_history is cleared on reset (losing export data), (c) whether the scenario selector reverts to its default value on reset, (d) whether Tab 3's selected_facility is cleared on reset. Given the immutable tick state constraint, a mid-tick reset should be safe — but the ordering of session state writes is not guaranteed across `st.rerun()` cycles.

**Impact:** A user who clicks Reset mid-demo will get different behaviour depending on the implementation. Clearing tick_history on reset loses all export data — a data-team user (Tab 4 persona) will be blocked from exporting after a reset. This is a low-probability but high-impact demo failure mode.

**Fix:** Add to §8.2: "Reset clears `st.session_state` simulation state (current_tick, active_alerts, active_reroutes) but preserves tick_history in `scenario_snapshots[scenario_id]` for export. The simulation loop is halted before reset executes (is_running = False is set atomically before state clear). Selected facility in Tab 3 is cleared."

---

### LOW — Performance NFR for Tab 2 simultaneous 5-network render has no implementation guidance

**Location:** §9 NFRs; §8.4 Tab 2

**Problem:** The NFR states "All 5 networks renderable on Tab 2 without perceptible lag" and §12 R-01 mitigation says "offload graph computation to background thread via st.cache_data." However, `st.cache_data` is a memoisation decorator, not a background threading mechanism. Background threads in Streamlit require `threading.Thread` or `concurrent.futures`, neither of which is thread-safe with `st.session_state` by default. The PRD does not specify which computations are cached vs. re-run per tick, what the cache key is (network_id + tick + seed?), or how cache invalidation works when a scenario fires a state-mutating alert. The 400ms per-tick NFR and the "5 networks simultaneously" requirement are in tension — 5 networks × betweenness centrality on 59-node graphs × `st.rerun()` = significant overhead.

**Impact:** Week 3 Tab 2 implementation will produce a slow, laggy demo on underpowered conference hardware unless caching strategy is pre-specified. Discovering this performance issue on day 4 of the sprint leaves no time to fix it.

**Fix:** Specify the caching strategy explicitly: "betweenness centrality and PageRank are computed once per tick per network and cached in `st.session_state.graph_cache[network_id][tick]`. Tab 2 mini-maps are rendered from cached values, not recomputed. The graph_cache is a plain dict, not `st.cache_data`, to avoid serialisation overhead."
