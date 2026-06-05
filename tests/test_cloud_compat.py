"""Cloud compatibility and deployment readiness tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path("data/scenarios")
REQUIREMENTS_PATH = Path("requirements.txt")

# Runtime deps that must appear in requirements.txt
REQUIRED_RUNTIME_DEPS = [
    "streamlit",
    "plotly",
    "networkx",
    "scipy",
    "pandas",
    "pyarrow",
    "pydantic",
    "pyyaml",
    "kaleido",
    "openpyxl",
]

# Dev-only packages that must NOT appear in requirements.txt
DEV_ONLY_DEPS = ["pytest", "pytest-cov", "ruff", "coverage"]


# ─── requirements.txt ────────────────────────────────────────────────────────

def test_requirements_txt_exists():
    assert REQUIREMENTS_PATH.exists(), "requirements.txt not found — run: uv export --format requirements-txt --no-hashes --no-dev > requirements.txt"


def test_requirements_txt_non_empty():
    assert REQUIREMENTS_PATH.stat().st_size > 0


def test_requirements_has_all_runtime_deps():
    content = REQUIREMENTS_PATH.read_text().lower()
    for dep in REQUIRED_RUNTIME_DEPS:
        assert dep.lower() in content, f"Missing runtime dep in requirements.txt: {dep}"


def test_requirements_excludes_dev_deps():
    content = REQUIREMENTS_PATH.read_text().lower()
    for dep in DEV_ONLY_DEPS:
        assert dep.lower() not in content, (
            f"Dev dep '{dep}' found in requirements.txt — regenerate with --no-dev flag"
        )


def test_requirements_has_version_pins():
    """Every package entry line should have a version pin (== or >=)."""
    lines = [
        ln.strip() for ln in REQUIREMENTS_PATH.read_text().splitlines()
        if ln.strip()
        and not ln.startswith("#")   # skip comment lines
        and not ln.startswith("-")   # skip -r / -c flags
        and not ln.startswith("Resolved")  # skip uv status line
        and ln[0].isalpha()          # must start with package name
    ]
    unpinned = [ln for ln in lines if "==" not in ln and ">=" not in ln]
    assert len(unpinned) == 0, f"Unpinned packages in requirements.txt: {unpinned}"


# ─── Pre-computed data ────────────────────────────────────────────────────────

def test_data_scenarios_dir_exists():
    assert DATA_DIR.exists(), "data/scenarios/ not found — run generate_scenarios.py --all"


def test_metadata_json_committed():
    assert (DATA_DIR / "metadata.json").exists()


def test_all_8_parquets_committed():
    for i in range(1, 9):
        parquet = DATA_DIR / f"sc-0{i}.parquet"
        assert parquet.exists(), f"Missing committed parquet: {parquet}"


def test_all_8_alert_jsons_committed():
    for i in range(1, 9):
        alerts = DATA_DIR / f"sc-0{i}_alerts.json"
        assert alerts.exists(), f"Missing committed alert JSON: {alerts}"


def test_data_total_size_under_2mb():
    total = sum(p.stat().st_size for p in DATA_DIR.glob("*.parquet"))
    total_kb = total / 1024
    assert total_kb < 2048, f"Parquet total {total_kb:.1f} KB exceeds 2 MB Cloud limit estimate"


# ─── App structure ────────────────────────────────────────────────────────────

def test_readme_exists():
    assert Path("README.md").exists()


def test_readme_has_cloud_section():
    content = Path("README.md").read_text()
    assert "Streamlit Cloud" in content
    assert "DIAGNET_SCREENSHOT_ENABLED" in content


def test_readme_has_local_setup():
    content = Path("README.md").read_text()
    assert "uv run streamlit run app.py" in content


def test_streamlit_config_exists():
    assert Path(".streamlit/config.toml").exists()


def test_streamlit_config_headless():
    content = Path(".streamlit/config.toml").read_text()
    assert "headless = true" in content


# ─── Screenshot env var gate ─────────────────────────────────────────────────

def test_screenshot_disabled_by_env_var(monkeypatch):
    """DIAGNET_SCREENSHOT_ENABLED=false must disable screenshot — Cloud safety check."""
    monkeypatch.setenv("DIAGNET_SCREENSHOT_ENABLED", "false")
    from tabs.export import is_screenshot_enabled
    assert is_screenshot_enabled() is False


def test_screenshot_enabled_by_default(monkeypatch):
    monkeypatch.delenv("DIAGNET_SCREENSHOT_ENABLED", raising=False)
    from tabs.export import is_screenshot_enabled
    assert is_screenshot_enabled() is True


# ─── No CDN dependencies ──────────────────────────────────────────────────────

def test_app_has_no_external_cdn_imports():
    """app.py must not reference any CDN URLs."""
    content = Path("app.py").read_text()
    cdn_patterns = ["cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com", "cdn.plot.ly"]
    for pattern in cdn_patterns:
        assert pattern not in content, f"CDN reference found in app.py: {pattern}"


def test_no_hardcoded_external_urls_in_viz():
    """viz/ modules must not contain external URLs."""
    for viz_file in Path("viz").glob("*.py"):
        content = viz_file.read_text()
        assert "http://" not in content or "localhost" in content, (
            f"External URL in {viz_file}"
        )


# ─── Module boundary ──────────────────────────────────────────────────────────

def test_app_does_not_import_generation():
    content = Path("app.py").read_text()
    assert "from generation" not in content
    assert "import generation" not in content


def test_tabs_do_not_import_generation():
    for tab_file in Path("tabs").glob("*.py"):
        content = tab_file.read_text()
        assert "from generation" not in content, f"generation/ import in {tab_file}"
        assert "import generation" not in content, f"generation/ import in {tab_file}"


def test_viz_does_not_import_generation():
    for viz_file in Path("viz").glob("*.py"):
        content = viz_file.read_text()
        assert "from generation" not in content, f"generation/ import in {viz_file}"
