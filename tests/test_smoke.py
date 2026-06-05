"""Smoke test — verifies project scaffold is correctly set up."""
import importlib.util
from pathlib import Path


def test_streamlit_importable():
    assert importlib.util.find_spec("streamlit") is not None


def test_plotly_importable():
    assert importlib.util.find_spec("plotly") is not None


def test_networkx_importable():
    assert importlib.util.find_spec("networkx") is not None


def test_app_stub_exists():
    assert Path("app.py").exists()


def test_streamlit_config_exists():
    config = Path(".streamlit/config.toml")
    assert config.exists()
    content = config.read_text()
    assert "headless = true" in content
    assert "gatherUsageStats = false" in content


def test_uv_lock_exists():
    assert Path("uv.lock").exists()


def test_requirements_txt_exists():
    assert Path("requirements.txt").exists()
