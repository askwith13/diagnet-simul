# Validation Report — DiagNet Simulation PRD

- **PRD:** `_bmad-output/planning-artifacts/Simulation PRD.md`
- **Rubric:** `.claude/skills/bmad-prd/assets/prd-validation-checklist.md`
- **Workspace:** `_bmad-output/planning-artifacts/prds/prd-DiagNet_Simul-2026-06-04/`
- **Run at:** 2026-06-04T00:00:00Z
- **Grade:** Poor

## Overall verdict

The PRD is technically rich and unusually specific for a hackathon context — the scenario table, tick-level alert sequence for SC-01, FacilityState field list, and NFR targets with measurement locations are genuine implementation scaffolding. However, four critical implementation blockers (GlobalState contract missing, node-click navigation unimplementable in standard Streamlit, SHAP stub algorithm unnamed, SC-08 orchestration unspecified) push the grade to Poor. The rubric additionally flags concentrated gaps in scope honesty (no [ASSUMPTION] tags, kaleido undisclosed, rpy2 in stack but deferred) and done-ness clarity (7 of 8 scenarios lack tick-level specs). Resolving the four criticals and the high findings in Done-ness and Scope Honesty would raise this to Good.

## Dimension verdicts

- Decision-readiness — Adequate
- Substance over theater — Strong
- Strategic coherence — Strong
- Done-ness clarity — Adequate
- Scope honesty — Thin
- Downstream usability — Adequate
- Shape fit — Strong

## Findings by severity

---

### Critical (4)

**[Adversarial]** — GlobalState inter-network data contract missing from data model (§4.3, §5.3, §12 R-05)
R-05 says "introduce a GlobalState container" but GlobalState appears nowhere in §5. No fields, no overflow_delta structure, no tick-synchronisation rule. SC-04 and SC-08 blocked. Two developers will invent incompatible schemas.
Fix: Add §5.4 GlobalState spec. Minimum fields: `network_states: Dict[str, NetworkState]`, `inter_network_flows: List[InterNetworkFlow]` (source_net, target_net, patient_count, tick), `global_tick: int`, `overflow_pending: Dict[str, float]`. Specify synchronous global tick. Specify who calls GlobalState.apply_overflow().

**[Adversarial]** — Node click → Tab 3 navigation has no specified implementation path (§8.5, §8.3)
Streamlit ≥1.35 `st.tabs()` has no programmatic tab-switching API. Tab 3 is the SHAP showcase — the single feature the Funder/Reviewer persona needs. Without a specified workaround, three incompatible implementations will emerge.
Fix: Capture plotly_click into `st.session_state.selected_facility`; render Tab 3 content using `st.expander` on the same page below the tab bar. Or remove "clicking any node" language and use a selectbox.

**[Adversarial]** — SHAP stub computation algorithm not specified (§7, §8.3, §8.5)
"Approximated from per_tick_deltas" is a name, not an algorithm. No base value, no mapping, no normalisation. SHAP is mandatory on every alert — this gap blocks every alert card's implementation.
Fix: For each field f with non-zero delta d_f: `shap_f = d_f × weight_f` (weight_f per-field constant in YAML). Baseline = facility value at tick 0. Top 5 by |shap_f| displayed. Include a worked numeric example for SC-01 tick 4.

**[Adversarial]** — SC-08 "Simulate all" orchestration unspecified (§6.1, §8.4)
No start-state definition, no multi-network YAML delta schema, no definition of "impact metrics." §8.4 says "Simulate all" runs SC-04; §6.1 assigns SC-08 to all networks. Direct conflict.
Fix: SC-08 starts from pre-loaded "post-crisis" YAML baselines. Add multi-network delta schema to §6.3. Define impact metrics as specific aggregates. Clarify "Simulate all" = SC-08; SC-04 is dropdown-only.

---

### High (11)

**[Rubric — Decision-readiness]** — v2 Bayesian scope boundary undefined (§3, §7, §12)
"rpy2 deferred to v2" stated three times but no version boundary or trigger condition defined. Architects cannot design the abstraction layer.
Fix: "v2 is out of scope for June submission; scipy stub is the final implementation."

**[Rubric — Decision-readiness]** — "About panel" missing from Tab structure (§2 vs. §8)
IT/Data persona references a data-source table in an About panel; §8 defines exactly 4 tabs.
Fix: Add Tab 5 / About modal spec to §8, or remove About panel reference from §2.

**[Rubric — Done-ness]** — Only SC-01 has tick-level alert sequences (§6)
SC-02–SC-08 have no tick-level specs. Regression test golden fixtures cannot be written for 7 of 8 scenarios.
Fix: Add 3–4 key tick/type/threshold-trigger rows for SC-02–SC-08.

**[Rubric — Done-ness]** — "Pulse ring on critical" undefined (§8, Tab 1)
No animation type, period, radius, or Plotly implementation approach.
Fix: Specify animation approach, or downgrade to static outer ring (see adversarial medium finding).

**[Rubric — Scope honesty]** — Screenshot mode kaleido dependency not flagged (§8, Tab 4)
plotly.io PNG export requires kaleido; not in stack; not in risks. Silent failure on restricted demo machines.
Fix: Add kaleido to §3.3 and add Risk R-08 with mitigation.

**[Rubric — Scope honesty]** — No [ASSUMPTION] tags anywhere (throughout)
Three load-bearing unmarked assumptions: synthetic data clinical plausibility, demo hardware context (laptop vs. server), SHAP approximation acceptability.
Fix: Add Assumptions Index (§A) with owner and validation plan per entry.

**[Rubric — Downstream usability]** — No functional requirement IDs (§4–§8)
Story writers cannot anchor to specific requirements. Manual text-matching in a 5-day sprint is a real time cost.
Fix: Add FR-NNN IDs to each named feature in §§4–8 (FR-101–FR-140 covers the dashboard layer).

**[Adversarial]** — Speed slider delta-scaling behaviour ambiguous (§8.2, §6.3)
"Controls both tick rate and per-tick state delta magnitude" — does 4× scale deltas or only animation rate? Incompatible implementations produce divergent alert timings.
Fix: "Speed controls only sleep_interval_s. Per-tick delta magnitudes invariant to speed setting."

**[Adversarial]** — effective_capacity formula has unit collision and undefined variables (§5.2)
`daily_consumption` and `max_samples_per_module` are not FacilityState fields. Left term = days, right term = samples/day — different units. feeds predicted_stockout_day.
Fix: `effective_capacity_days = cartridges / samples_per_module_per_day`. Remove dimensionally inconsistent right term.

**[Adversarial]** — Screenshot mode scope and implementation path undefined (§8.6)
Full dashboard cannot be captured by plotly.io.write_image (single-figure API). "Current" is ambiguous.
Fix: Narrow to active Plotly figure only. Add kaleido to dependencies. Specify simulation must be paused before capture.

**[Adversarial]** — Alert message interpolation engine unspecified (§6.3)
f-string syntax in YAML with no namespace spec, no missing-key handling. Runtime KeyError in a live demo is catastrophic.
Fix: str.format_map() against FacilityState.__dict__ of first affected facility. Missing keys → literal key in brackets. Provide safe-format helper in core/models.py.

**[Adversarial]** — tick_history O(n²) space blowup with immutable state (§5.3, §9)
If tick snapshots include full NetworkState (which includes tick_history), serialisation is recursive. SC-08 at 35 ticks × 5 networks risks RecursionError or multi-second export.
Fix: Each tick_history entry is a flat dict: `{tick: int, facility_id: str, **facility_state_fields}`. tick_history excluded from NetworkState serialisation snapshots.

---

### Medium (12)

**[Rubric — Decision-readiness]** — Tab 3 interaction model not decided (§8)
Plotly clickData in Streamlit requires a specific session_state pattern not documented.
Fix: "Node click triggers st.session_state['selected_facility'] via plotly_click callback."

**[Rubric — Substance]** — M3 GCN stub is innovation theater (§7)
No demo moment, no AC, no scenario. 128-dim embeddings are internal/not shown.
Fix: Label M3 as "v2 placeholder, not implemented in v1." Decouple M4 from M3.

**[Rubric — Done-ness]** — "Recommended actions — 3 bullets" source ambiguous (§8, Tab 3)
Hardcoded YAML vs. dynamic state is an architecture decision.
Fix: "Pre-authored strings in scenario YAML keyed by (scenario_id, tick_range, facility_id)."

**[Rubric — Done-ness]** — No YAML skeleton for SC-02–SC-08 (§6)
data_generator.py author cannot produce consistent test fixtures.
Fix: Add per_tick_deltas skeleton YAML for each remaining scenario.

**[Rubric — Scope honesty]** — Config editor write-back silently cut (§8, Tab 4)
"Read-only + download" scope reduction not in Non-Goals.
Fix: Add "In-app YAML editing with write-back" to §1 Non-Goals.

**[Rubric — Scope honesty]** — rpy2 in tech stack but deferred (§3, §12)
Creates confusion about what v1 actually builds.
Fix: Move rpy2 to a "v2 dependencies" subsection in §3.3.

**[Rubric — Downstream usability]** — "node2vec" missing from glossary (§7, §13)
Non-technical reviewers will not know this term.
Fix: Add definition to §13.

**[Rubric — Shape fit]** — Week 3 AC "all 8 scenarios run" is unverifiable (§10)
Without tick specs for SC-02–SC-08, "runs" cannot be tested. Blocks demo rehearsal scheduling.
Fix: Resolving the SC-02–SC-08 tick spec gap (Done-ness High) addresses this simultaneously.

**[Adversarial]** — Pulsing ring animation technically incompatible with Streamlit rerun model (§8.3)
Plotly frame animation at 1.2 Hz conflicts with 400ms tick render budget. Sprint time sink risk.
Fix: Downgrade to static outer ring at 1.5× radius with 0.4 opacity. Pulse deferred to v2.

**[Adversarial]** — Scenario comparison requires two run histories with no state isolation spec (§8.6)
No spec for post-hoc vs. concurrent comparison, session_state collision prevention, or control ownership.
Fix: "Post-hoc only. Completed scenarios saved to scenario_snapshots[scenario_id]. Tab 4 compares any two saved snapshots."

**[Adversarial]** — Alert panel persistence and deduplication rules absent (§8.3)
No spec for persistence across ticks, deduplication, per-network vs. global scope, or tick-0 state.
Fix: "14 most recent AlertRecords from selected network. Persist for scenario lifetime. Same-tick deduplication. Tick-0 placeholder text."

**[Adversarial]** — "Simulate all" button conflicts with SC-04 assignment (§8.4 vs. §6.1)
§8.4 says button runs SC-04; §6.1 assigns SC-08 to all networks.
Fix: "Simulate all" = SC-08. SC-04 is dropdown-only.

**[Adversarial]** — M3 → M4 dependency chain architecturally inconsistent (§7)
M4 uses Dijkstra (edge weights), not node embeddings. M3 "input to M4" claim is misleading. node2vec package not in stack.
Fix: Decouple M4 from M3. M4 = Dijkstra + pre-loaded Q-table YAML. M3 = v2 placeholder.

---

### Low (10)

**[Rubric — Strategic coherence]** — No explicit demo success definition (§1, §2)
Fix: 3-bullet "Demo success criteria" in §1.

**[Rubric — Strategic coherence]** — No counter-metrics on AI output ranges (§6, §7)
Fix: Per-model output range expectations in §7.

**[Rubric — Substance]** — Developer personas in §2 are credits not personas (§2)
Fix: Move names to Acknowledgements footer.

**[Rubric — Downstream usability]** — inter_network_links absent from NetworkState schema (§4 vs. §5)
Fix: Add `inter_network_links: List[Tuple[str, str, str]]` to §5.3.

**[Rubric — Done-ness]** — "Demo video recorded" is not a software AC (§10, Week 3)
Fix: Replace with screenshot regression test criterion.

**[Rubric — Shape fit]** — Flat document structure makes subsystem extraction manual (§§3–8)
Fix: Add "Simulation Core" vs. "Presentation Layer" subsection headers.

**[Rubric — Scope honesty]** — Non-Goals cover only production concerns, not demo-scope cuts (§1)
Fix: Add multi-user sessions, auth, real-time data ingestion to Non-Goals.

**[Adversarial]** — Inter-network link YAML schema absent (§4.3, §11.1)
Fix: Add top-level inter_network_links key to §11.1 with typed example.

**[Adversarial]** — WCAG AA alert card colours will fail as specified (§9, §8.3)
#ef4444 on white = 4.0:1 (fails AA). #f59e0b on white = 2.8:1 (fails AA).
Fix: CRITICAL = #dc2626/white (4.5:1); DTO ADVISORY = #f59e0b card with #92400e text (7.3:1); BAYESIAN = #1d4ed8/white (5.9:1).

**[Adversarial]** — Reset button behaviour during active run unspecified (§8.2)
Fix: "Reset preserves tick_history in scenario_snapshots. Halts sim before clearing. Clears selected_facility."

**[Adversarial]** — Tab 2 caching strategy uses wrong mechanism (§9, §12 R-01)
st.cache_data is memoisation, not background threading.
Fix: "betweenness + PageRank cached in st.session_state.graph_cache[network_id][tick] (plain dict). Tab 2 renders from cache."

---

## Mechanical notes

- **AI model count discrepancy:** §7 says "4 stubs" but lists 6 (B1, B2, M1, M2, M3, M4). Fix header to "6 AI model stubs (4 active in v1 demo, 2 internal/deferred)."
- **Glossary gap:** "node2vec" (§7) absent from §13.
- **Broken cross-reference:** "About panel" (§2) does not resolve to any element in §8.
- **Broken cross-reference:** "Config editor — read-only + download" (§8) implies scope cut not in §1 Non-Goals.
- **FR IDs absent:** SC-01–SC-08 and NET-A–NET-E contiguous; R-01–R-07 contiguous. No FR-NNN IDs exist.
- **Assumptions Index:** Does not exist. Three load-bearing unmarked assumptions identified.
- **Tick count inconsistency:** §10 visual QA references tick 25; SC-04/SC-05/SC-08 run to 30–35 ticks. Add tick-30 and tick-35 QA checkpoints.

## Reviewer files

- `review-rubric.md`
- `review-adversarial.md`
