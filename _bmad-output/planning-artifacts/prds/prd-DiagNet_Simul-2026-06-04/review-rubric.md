# PRD Quality Review — DiagNet Simulation PRD

## Overall verdict

This PRD is technically rich and unusually specific for a hackathon-context document: the scenario table, tick-level alert sequences, FacilityState field list, and NFR targets with measurement hooks are genuine implementation scaffolding rather than filler. The primary risks are concentrated in done-ness clarity (adjective-heavy Acceptance Criteria at the story boundary), a thin scope-honesty section that leaves three real tensions unresolved, and one downstream-usability gap — the lack of unique IDs on FRs — which will make story creation slower than it needs to be given the 5-day sprint timeline.

---

## 1. Decision-readiness — adequate

The PRD surfaces several real trade-offs explicitly: brms/Stan deferred to v2 (R-04), SHAP statistical rigour acknowledged (R-03), Tab 2 performance risk (R-01), and the inter-network sync problem (R-05). These are actual choices, not false balancing. The risk table gives likelihoods and mitigations, which is more than most PRDs at this stage.

However, two decisions are still open that would block architecture choices right now:

1. The Bayesian engine version split (scipy stub v1 vs. rpy2 v2) is described in §3, §7, and §12 but the boundary conditions for v2 are never stated. A reviewer cannot tell whether the v2 upgrade is in-scope for this submission or a separate product milestone. Given the June 9-10 deadline, this ambiguity is consequential.

2. The "About panel" referenced in §2 (persona: "IT/Data team — Data source table in About panel") does not appear in §8's 4-tab dashboard spec. Either this is a fifth tab, a modal, or a footer element — the decision is nowhere. An architect designing the Streamlit layout cannot proceed.

The Open Questions section is genuinely about real risks (not aspirational "questions"), but seven items for a 59-node, 5-day build feels under-enumerated. Specifically missing: Streamlit multi-page vs. single-page choice, whether Tab 3 node-click is a Plotly callback or a sidebar select, and the brms v2 scope boundary.

### Findings
- **High** v2 Bayesian scope boundary undefined (§3, §7, §12) — "v1 scipy stub only; rpy2 deferred to v2" is stated three times but no version boundary or trigger condition is defined. Architects cannot design the data model abstraction layer. *Fix:* Add a one-line decision: "v2 is out of scope for June submission; scipy stub is the final implementation unless explicitly re-scoped."
- **High** "About panel" missing from Tab structure (§2 vs. §8) — Persona table references a data-source table in an About panel; §8 defines exactly 4 tabs with no About. *Fix:* Either add Tab 5 / About modal to §8 spec, or remove the About panel reference from §2.
- **Medium** Streamlit interaction model for Tab 3 not decided (§8) — "Accessed by clicking node" is stated but Plotly clickData callbacks in Streamlit require a specific session_state pattern. Not flagging this as a NFR gap but as a missing architectural decision that will cause re-work in story creation. *Fix:* Add one line: "Node click triggers st.session_state['selected_facility'] via plotly_click callback; Tab 3 reads this key."

---

## 2. Substance over theater — strong

This PRD avoids the most common theater failures. Personas in §2 are tied to specific observable demo moments ("Node turns amber → tooltip shows metrics"), not role descriptions. NFRs in §9 all carry numeric targets with named measurement methods — no NFR says "fast" or "secure." The vision in §1 is specific to NTEP/India/CBNAAT; the one-line summary cannot be swapped into a generic health platform PRD.

One instance of mild theater exists in the AI model section:

- M3 (GCN embeddings, node2vec approximation, 128-dim, internal/not shown) has no demo moment, no alert tied to it, no AC, and no scenario that exercises it. It exists in §7 but is invisible to the dashboard spec, the scenario spec, and the implementation plan. This is innovation theater: the term "GCN" signals technical sophistication but zero product decisions depend on it.

The SHAP explainability mandate ("SHAP explainability mandatory on every alert" — §7) is strong substance: it forces a specific UI contract and drives both the YAML schema (per_tick_deltas as SHAP proxy) and the tooltip spec.

### Findings
- **Medium** M3 GCN stub is innovation theater (§7) — 128-dim embeddings are "internal, not shown in demo" with no scenario, no AC, no dashboard element. If it exists only to say "we have GCN," remove it or move it to a v2 backlog note. *Fix:* Either add a Tab 4 export that surfaces embedding distances, or explicitly label M3 as "v2 placeholder, not implemented in v1."
- **Low** Developer audience personas (§2) carry names but no decision-driving information — "Tech Writing Lead (Dr Nitiksha)" tells an architect nothing about what this person needs from the codebase or demo. These are credits, not personas. *Fix:* Move developer names to an Acknowledgements footer; keep only the decision-relevant primary personas in §2.

---

## 3. Strategic coherence — strong

The thesis is clear and consistent: "show NTEP stakeholders that AI-assisted network intelligence prevents diagnostic failures before they cascade." Every major feature — 8 scenarios, 4 AI model stubs, SHAP explainability, inter-network connections — serves this thesis. The scenario arc from single-failure (SC-01–SC-03) to multi-failure (SC-04–SC-05) to recovery (SC-08) is a deliberate demonstration narrative, not a random feature list.

Success metrics are implicit rather than stated. The PRD has no explicit "success = X" section, but the demo moments in §2 and the scenario AC ("all alerts fire at correct ticks") functionally serve as success criteria. For a simulation platform this is acceptable, but the absence of an explicit metric creates a risk: if the demo goes well but TAT charts are blank, does that count as failure? For a stakeholder review context, stating "the demo is successful if all 8 scenarios run to completion with no Python traceback visible to the audience" would be valuable.

Counter-metrics are absent. There is no acknowledgement of what a "too good" simulation would look like (e.g., if alerts fire too early, they become noise; if the network never fails, the AI models have no demonstration value).

### Findings
- **Low** No explicit success definition (§1, §2) — Demo moments exist but no stated pass/fail threshold for the June presentation. *Fix:* Add a 3-bullet "Demo success criteria" to §1: e.g., "All 8 scenarios complete without traceback; SHAP panel visible on at least one alert per scenario; Tab 2 renders 5 networks without perceptible lag."
- **Low** No counter-metrics (§6, §7) — If Bayesian stockout probability is always >0.90 in SC-03, the model is not discriminating. No floor/ceiling bounds on AI output ranges to keep them credible. *Fix:* Add per-model output range expectations to §7 (e.g., "B1 output P(stock≤0) ranges 0.20–0.95 across scenarios; M1 anomaly score ranges 0.30–0.95").

---

## 4. Done-ness clarity — adequate

The scenario-level AC in §10 is far stronger than typical PRDs: "SC-01, SC-02, SC-03 run on NET-A; all alerts fire at correct ticks; SHAP stubs display" gives an engineer a specific test. The NFR table in §9 is excellent — every row has a target, a unit, and a measurement location. The immutable-tick-state constraint in §3 is an unusually precise architectural AC.

The weaknesses are at the feature-level (FRs are described in prose, not as discrete FR-NNN items) and in a cluster of adjective-laden phrases that will create ambiguity in story writing:

- §8 Tab 1: "pulse ring on critical" — what is the ring? Animated? SVG circle? Plotly shape? What defines the animation period?
- §8 Tab 1: "14 most recent" alerts — does this mean 14 visible at a time (scrollable overflow?) or exactly 14 total?
- §8 Tab 3: "3 bullets" recommended actions — are these hardcoded per scenario in YAML, or generated dynamically from alert state?
- §8 Tab 2: "without perceptible lag" (NFR row) — contradicted by the NFR table which says "FPS counter in debug mode." The NFR table is good; the prose is redundant and less precise.
- §10 Week 3 AC: "demo video recorded" is an output artifact, not an acceptance criterion for the software.

The tick-level alert sequence defined for SC-01 (§6) is the strongest done-ness signal in the document. If this level of specification existed for all 8 scenarios, story creation would be near-mechanical. Currently only SC-01 has it.

### Findings
- **High** Only SC-01 has tick-level alert sequences (§6) — SC-02 through SC-08 have no tick-level specs, making story-level AC underspecified for 7 of 8 scenarios. An engineer cannot write a regression test fixture without these. *Fix:* Add tick/type/metric-threshold trigger tables for SC-02–SC-08, even if abbreviated (3-4 key ticks per scenario is sufficient).
- **High** "Pulse ring on critical" undefined (§8, Tab 1) — No spec for animation type, period, radius, or Plotly implementation approach. *Fix:* "Animated Plotly scatter marker with size oscillating between 1× and 1.4× node radius at 1Hz via frame-based animation or CSS; triggered when status='critical'."
- **Medium** "Recommended actions — 3 bullets" source ambiguous (§8, Tab 3) — Hardcoded YAML vs. dynamic state-derived content is an architecture decision, not a display decision. *Fix:* "Recommended actions are pre-authored strings in scenario YAML keyed by (scenario_id, tick_range, facility_id); displayed verbatim in Tab 3."
- **Medium** SC-01 to SC-08 scenario YAML schema defined (§6) but no example YAML for SC-02–SC-08 — data_generator.py author cannot produce consistent test fixtures. *Fix:* Add one complete YAML block per remaining scenario, or at minimum a per_tick_deltas skeleton.
- **Low** "Demo video recorded" as AC (§10, Week 3) — This is a deliverable, not software AC. *Fix:* Replace with "Screenshot regression test passes at ticks 0, 7, 15, 25 for all scenarios."

---

## 5. Scope honesty — thin

The Non-Goals in §1 ("Out of scope for v1.0") lists four items, all of which are large production features (NIKSHAY connections, patient data, mobile, federated learning). This is genuine out-of-scope work, but none of these are tensions the team is likely to debate during the sprint.

The real scope tensions — the ones that will cause re-work if unresolved — are not surfaced:

1. **Tab 3 node-click interaction** (mentioned in §8) implies Plotly clickData callback. This requires Streamlit component re-rendering logic that is non-trivial and not noted as a risk or assumption.
2. **Screenshot mode (PNG 1920×1080)** in Tab 4 — generating a static PNG from a live Streamlit/Plotly app requires either plotly.io.write_image (needs kaleido) or browser screenshot automation. Kaleido is a non-trivial dependency; neither path is mentioned in the stack or as a risk.
3. **brms/Stan rpy2 dependency** is Risk R-04 but the v1 mitigation ("scipy stub only") is not reflected as a Non-Goal. A reviewer could legitimately ask "why is rpy2 in the tech stack if it's deferred?"
4. **Config editor (read-only + download)** in Tab 4 — editing YAML in a running Streamlit app is non-trivial. "Read-only + download" is a scope reduction that should be tagged [ASSUMPTION] or added to Non-Goals.

There are zero [ASSUMPTION] tags or [NOTE FOR PM] callouts in the document. For a document feeding architecture and epics, this is a gap. Assumptions about synthetic data representativeness (are the 59 node baseline states clinically validated?), about demo environment hardware (single laptop? cloud instance?), and about the SHAP approximation adequacy are all embedded silently.

### Findings
- **High** Screenshot mode dependency on kaleido not flagged (§8, Tab 4) — plotly.io PNG export requires kaleido package; not in tech stack; not in risks. On a restricted demo machine this fails silently. *Fix:* Add to tech stack ("kaleido for static export") and add Risk R-08: "kaleido unavailable on demo machine; mitigation: bundle or fallback to browser screenshot via pyautogui."
- **High** No [ASSUMPTION] tags anywhere — Three load-bearing assumptions are unmarked: (a) synthetic baseline states are clinically plausible enough for domain expert reviewers; (b) demo runs on a laptop (not a server), affecting performance NFR interpretation; (c) SHAP approximation from per_tick_deltas is acceptable to technical reviewers. *Fix:* Add an Assumptions Index (§A) with at minimum these three items, each with owner and validation plan.
- **Medium** Config editor scope reduction not stated as Non-Goal (§8, Tab 4) — "Read-only + download" implies write-back is cut; this is a scope decision not flagged in §1 Out of Scope. *Fix:* Add "In-app YAML editing with write-back" to Non-Goals.
- **Medium** rpy2 in tech stack but deferred (§3, §12) — Creates confusion about what is actually being built. *Fix:* Move rpy2 to a "v2 dependencies" subsection in §3, separate from v1 stack.
- **Low** Non-Goals cover only production concerns, not demo-scope cuts (§1) — Several demo features could be construed as in-scope (e.g., real-time WebSocket updates, auth, multi-user sessions). Adding 2-3 demo-specific non-goals would reduce stakeholder scope-creep during the review. *Fix:* Add "Multi-user concurrent sessions; authentication; real-time data ingestion from any source."

---

## 6. Downstream usability — adequate

**UX extraction:** Tab structure, persistent top bar, node encoding, edge encoding, alert panel dimensions (220px fixed), and time-series chart types are all specified with enough fidelity for a UX designer to produce wireframes without ambiguity. The demo moment column in §2 maps directly to Tab 1 and Tab 2 features. This is good.

**Architecture extraction:** Module table in §3 with file paths and responsibilities is architecture-ready. The data flow diagram (prose, §3) is clear. The immutable tick state constraint (§3) is a key architectural decision stated explicitly. The FacilityState field list with 16 fields and thresholds (§5) is directly usable as a data model spec.

**Story creation extraction:** This is where downstream usability degrades. The PRD has no functional requirement IDs (FR-NNN). Scenarios are numbered SC-01–SC-08 and modules are named, but individual features within tabs have no IDs. A story writer pulling "pulse ring on critical nodes" has no anchor to cite. Cross-referencing "SHAP waterfall panel on any alert" (§2) to "SHAP waterfall (top-5 features)" (§8, Tab 3) to "SHAP stubs display" (§10, Week 2 AC) requires manual text matching.

**Glossary:** 26 terms defined in §13. Spot-check: "cascade dropout" appears in §5 (field name: cascade_dropout_risk), §4 (scenario challenge label), and §2 (implied in demo moment), all consistent. "CBNAAT" defined. "GCN" defined. No drift detected in spot-check, but "node2vec" (used in §7) is not in the glossary.

**ID continuity:** Scenarios SC-01–SC-08 are contiguous. Network IDs NET-A–NET-E are contiguous. No FR-NNN IDs exist. Risk IDs R-01–R-07 are contiguous (R-08 noted as missing above).

### Findings
- **High** No functional requirement IDs (§4–§8) — Story writers cannot anchor to "FR-042: pulse ring" or cross-reference between PRD sections. In a 5-day sprint, manual text hunting is a real time cost. *Fix:* Add FR-NNN IDs to each named feature in §§4–8. A minimal approach: number each bullet/row in §8's tab spec (FR-101 through FR-140 is sufficient coverage).
- **Medium** "node2vec" not in glossary (§7, §13) — Used as the M3 implementation approach; non-technical reviewers will not know this term. *Fix:* Add "node2vec: graph embedding technique that uses random walks to produce vector representations of nodes; used here as a lower-complexity approximation of full GCN training."
- **Low** Inter-network connection topology defined (§4) but not reflected in NetworkState schema (§5) — NetworkState has network_id and graph_metrics but no inter_network_links field. An architect building GlobalState (R-05 mitigation) has no schema anchor. *Fix:* Add inter_network_links: List[Tuple[str, str, str]] to NetworkState fields in §5.

---

## 7. Shape fit — strong

This PRD is correctly shaped for its context. It is a demo/simulation platform with a hard submission deadline (9-10 June), a chain-top position (PRD → architecture → epics → stories), and a dual audience (technical reviewers + non-technical stakeholders). The PRD correctly:

- Provides tick-level scenario specs (needed for regression test fixtures in the sprint)
- Specifies demo moments per persona rather than user journey flows (correct for a simulation, not a product)
- Includes a module table with file paths (directly usable for architecture)
- Scopes to 5 networks × 8 scenarios × 4 AI stubs (ambitious but bounded for a 3-week build)
- Uses an implementation plan (§10) structured as week-level milestones with module build order — appropriate for a sprint, not over-engineered

The shape fails in one respect: the implementation plan's Week 3 AC ("All 8 scenarios run") treats scenario correctness as a binary deliverable, but with 7 scenarios having no tick-level spec, "runs" is unverifiable. This is a done-ness problem that also manifests as a shape problem — the demo rehearsal cannot be scheduled if it's unclear what "passes."

One structural shape note: the PRD is presented as a single flat document. For architecture and epic extraction, a two-section structure (Simulation Core vs. Dashboard/UI) would reduce cognitive load for downstream consumers. This is a recommendation, not a finding.

### Findings
- **Medium** Week 3 AC "all 8 scenarios run" is unverifiable without tick specs for SC-02–SC-08 (§10) — Directly blocks demo rehearsal scheduling. This is both a done-ness gap (Dimension 4) and a shape gap: a hackathon PRD feeding a sprint must have verifiable AC at each weekly milestone. *Fix:* Cross-reference this finding to the SC-02–SC-08 tick spec gap (Dimension 4, High finding); resolving that one fix addresses both.
- **Low** Single flat document structure makes architecture/epic extraction manual (§§3–8) — For chain-top documents, a "Simulation Core" vs. "Dashboard/UI" split in the section header hierarchy would allow epic writers to scope to one subsystem. *Fix:* Add subsection headers grouping §§3–6 as "Simulation Core" and §§7–8 as "Presentation Layer."

---

## Mechanical notes

- **Glossary gap:** "node2vec" (§7) is absent from the 26-term glossary (§13). "M3" and "M4" are used as model codes in §7 but the model count table lists B1, B2, M1, M2, M3, M4 — six models, yet §7 prose says "4 stubs." The header says "4 stubs" but then lists 6 items (B1, B2, M1, M2, M3, M4). This is a count error that may confuse reviewers.
- **ID continuity:** FR IDs are absent (not broken, absent). SC-01–SC-08 contiguous. NET-A–NET-E contiguous. R-01–R-07 contiguous; R-08 slot is implicitly consumed by the kaleido finding above.
- **Assumptions Index roundtrip:** No Assumptions Index exists. Three load-bearing assumptions identified (synthetic data clinical plausibility, demo hardware context, SHAP approximation adequacy) are embedded in prose with no owner or validation plan.
- **Cross-reference gap:** "About panel" (§2) does not resolve to any element in §8. "Config editor" in §8 is described as "read-only + download" but §1 Non-Goals does not list write-back as out of scope. These are broken cross-references, not just omissions.
- **AI model count discrepancy:** Section header §7 says "4 stubs" but enumerates B1, B2, M1, M2, M3, M4 (six items). *Fix:* Change header to "6 AI model stubs (4 active in v1 demo, 2 internal/deferred)" and clarify which four are demo-active.
- **Tick count inconsistency:** SC-08 (full network recovery, 35 ticks) is the longest scenario. §10 Week 3 AC references "tick 25" visual QA checkpoints. SC-04, SC-05, SC-08 all run beyond tick 25. Visual QA checklist should include tick 30 and tick 35 checkpoints.
