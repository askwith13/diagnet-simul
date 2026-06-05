# DiagNet — Diagnostic Network Intelligence for TB Care

AI-powered simulation platform for India's National TB Elimination Programme (NTEP).
Demonstrates multi-hub network intelligence across 5 districts, 59 facilities, and 8 scenarios.

**Hackathon submission — June 9-10, 2026 · PATH South Asia Digital Health**

---

## Quick Start (Local)

```bash
# 1. Install dependencies
uv add streamlit plotly networkx scipy pandas pyarrow pydantic pyyaml kaleido openpyxl
uv add --dev pytest pytest-cov ruff

# 2. Generate pre-computed scenario data (run once; re-run if YAMLs change)
uv run python scripts/generate_scenarios.py --all --validate

# 3. Launch the app
uv run streamlit run app.py
```

The app opens at http://localhost:8501.

---

## Project Structure

```
diagnet_simul/
├── app.py                   # Streamlit entry point
├── loader.py                # Data loading helpers
├── session.py               # Session state key constants
├── playback.py              # Tick advancement logic
├── config/
│   ├── networks.yaml        # 59 facilities across 5 networks
│   └── scenarios/           # 8 scenario YAML files
├── core/
│   ├── models.py            # Shared data contracts (FacilityState, FlatTickSnapshot, …)
│   └── network_layout.py    # Facility layout helpers
├── generation/              # Build-time pipeline (never imported at runtime)
│   ├── engine.py            # ScenarioGenerator + AI stubs
│   ├── scenario_config.py   # YAML → ScenarioConfig loader
│   └── shap_calculator.py   # SHAP approximation
├── scripts/
│   └── generate_scenarios.py# CLI: --all | --scenario SC-01 | --validate
├── data/scenarios/          # Pre-computed parquet + JSON outputs (committed)
├── viz/
│   ├── network_map.py       # Plotly network map builder (stateless)
│   └── alerts.py            # Alert card + SHAP bar renderer (stateless)
└── tabs/
    ├── network.py           # Tab 1 — Network Map
    ├── overview.py          # Tab 2 — Multi-Hub Overview
    ├── facility.py          # Tab 3 — Facility Detail
    └── export.py            # Tab 4 — Analytics & Export
```

---

## Regenerating Scenario Data

If you modify `config/networks.yaml` or any `config/scenarios/*.yaml`, regenerate:

```bash
# Regenerate all 8 scenarios
uv run python scripts/generate_scenarios.py --all --validate --force

# Regenerate one scenario only
uv run python scripts/generate_scenarios.py --scenario SC-01 --validate --force
```

---

## Running Tests

```bash
# Full suite (106 tests across generation, viz, playback, and tab helpers)
uv run pytest

# With coverage report
uv run pytest --cov=core --cov=generation --cov-fail-under=80
```

---

## Streamlit Cloud Deployment (Backup Demo)

> **For demo day:** run locally as primary. Use Cloud as backup if hardware fails.

### One-time setup

1. Push to a public GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app.
3. Select the repo, branch `main`, main file `app.py`.
4. Under **Advanced settings → Secrets**, add:
   ```toml
   DIAGNET_SCREENSHOT_ENABLED = "false"
   ```
5. Deploy. Cold start takes ~60 seconds on first load.

### Cloud URL

```
https://diagnet-simul.streamlit.app
```

> Update this URL after deployment.

### Cloud behaviour differences from local

| Feature | Local | Cloud |
|---|---|---|
| Screenshot (PNG export) | ✅ Enabled (kaleido) | ❌ Disabled via env var |
| All 8 scenarios | ✅ | ✅ |
| Playback speed | ✅ | ✅ (may be slightly slower) |
| Offline operation | ✅ | ✗ (requires internet) |

---

## Architecture Notes

- **Pre-computed data:** All scenario outputs are pre-computed offline and committed to `data/scenarios/`. The Streamlit app is a pure reader — no NetworkX or scipy at runtime.
- **Import boundary:** `generation/` is build-time only. It is never imported by `app.py`, `viz/`, or `tabs/`.
- **Session state keys:** Always imported from `session.py` — never raw strings.
- **SHAP approximation:** Labelled "Approximate · simulation mode" in all displays.

---

## Team

PATH South Asia Digital Health — DiagNet Team (Hackathon 2026)
