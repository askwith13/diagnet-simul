"""Tests for tabs/export.py — pure helper functions and JSON serialisation benchmark."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from loader import load_scenario_payloads
from tabs.export import (
    COMPARISON_METRICS,
    build_comparison_figure,
    is_screenshot_enabled,
)


@pytest.fixture(scope="module")
def payloads() -> dict:
    return load_scenario_payloads()


@pytest.fixture(scope="module")
def sc01_df(payloads) -> pd.DataFrame:
    return payloads["sc-01"]["tick_df"]


@pytest.fixture(scope="module")
def sc03_df(payloads) -> pd.DataFrame:
    return payloads["sc-03"]["tick_df"]


# ─── is_screenshot_enabled ───────────────────────────────────────────────────

def test_is_screenshot_enabled_default_true(monkeypatch):
    monkeypatch.delenv("DIAGNET_SCREENSHOT_ENABLED", raising=False)
    assert is_screenshot_enabled() is True


def test_is_screenshot_enabled_false_when_env_false(monkeypatch):
    monkeypatch.setenv("DIAGNET_SCREENSHOT_ENABLED", "false")
    assert is_screenshot_enabled() is False


def test_is_screenshot_enabled_case_insensitive(monkeypatch):
    monkeypatch.setenv("DIAGNET_SCREENSHOT_ENABLED", "FALSE")
    assert is_screenshot_enabled() is False


def test_is_screenshot_enabled_true_explicit(monkeypatch):
    monkeypatch.setenv("DIAGNET_SCREENSHOT_ENABLED", "true")
    assert is_screenshot_enabled() is True


# ─── build_comparison_figure ─────────────────────────────────────────────────

def test_build_comparison_figure_returns_figure(sc01_df, sc03_df):
    fig = build_comparison_figure(sc01_df, sc03_df, "patients_queued", "SC-01", "SC-03")
    assert isinstance(fig, go.Figure)


def test_build_comparison_figure_has_two_traces(sc01_df, sc03_df):
    fig = build_comparison_figure(sc01_df, sc03_df, "patients_queued", "SC-01 Net Bottleneck", "SC-03 Bayesian")
    assert len(fig.data) == 2


def test_build_comparison_figure_distinct_colours(sc01_df, sc03_df):
    fig = build_comparison_figure(sc01_df, sc03_df, "patients_queued", "SC-01", "SC-03")
    colour_a = fig.data[0].line.color
    colour_b = fig.data[1].line.color
    assert colour_a != colour_b


def test_build_comparison_figure_labelled_with_scenario_names(sc01_df, sc03_df):
    fig = build_comparison_figure(sc01_df, sc03_df, "patients_queued", "Network bottleneck", "Predicted stockout")
    names = [t.name for t in fig.data]
    assert "Network bottleneck" in names
    assert "Predicted stockout" in names


def test_build_comparison_figure_empty_df_returns_empty():
    fig = build_comparison_figure(pd.DataFrame(), pd.DataFrame(), "patients_queued", "A", "B")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_comparison_figure_unknown_metric_returns_empty(sc01_df, sc03_df):
    fig = build_comparison_figure(sc01_df, sc03_df, "nonexistent_field", "A", "B")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 0


def test_build_comparison_figure_sum_metric_patients_queued(sc01_df, sc03_df):
    """patients_queued uses sum aggregation — values should be larger than individual facility values."""
    fig = build_comparison_figure(sc01_df, sc03_df, "patients_queued", "SC-01", "SC-03")
    y_a = list(fig.data[0].y)
    # Sum across 59 facilities > baseline of any single facility
    assert max(y_a) > 100


def test_build_comparison_figure_mean_metric_cascade_risk(sc01_df, sc03_df):
    """cascade_dropout_risk uses mean aggregation — values should be [0, 1]."""
    fig = build_comparison_figure(sc01_df, sc03_df, "cascade_dropout_risk", "SC-01", "SC-03")
    y_a = list(fig.data[0].y)
    assert all(0.0 <= v <= 1.0 for v in y_a)


def test_build_comparison_figure_tick_axis(sc01_df, sc03_df):
    """X axis should span the scenario's tick range."""
    fig = build_comparison_figure(sc01_df, sc03_df, "patients_queued", "SC-01", "SC-03")
    x_a = list(fig.data[0].x)
    assert min(x_a) == 0
    assert max(x_a) == sc01_df["tick"].max()


def test_build_comparison_figure_all_metrics_work(sc01_df, sc03_df):
    """Every metric in COMPARISON_METRICS should produce a valid figure."""
    for metric in COMPARISON_METRICS:
        fig = build_comparison_figure(sc01_df, sc03_df, metric, "A", "B")
        assert isinstance(fig, go.Figure), f"Failed for metric: {metric}"
        if metric in sc01_df.columns:
            assert len(fig.data) == 2, f"Expected 2 traces for metric: {metric}"


# ─── Networks.yaml availability ──────────────────────────────────────────────

def test_networks_yaml_readable():
    from tabs.export import NETWORKS_YAML_PATH
    assert NETWORKS_YAML_PATH.exists()
    content = NETWORKS_YAML_PATH.read_text()
    assert len(content) > 0
    assert "networks:" in content


# ─── JSON serialisation benchmark (NFR8) ─────────────────────────────────────

def test_json_serialisation_benchmark(sc01_df):
    """Full tick history (25 ticks × 59 facilities × 22 fields) serialises in < 500ms."""
    # Convert to list of flat dicts as the export would
    records = sc01_df.to_dict(orient="records")

    # Replace NaN with None for JSON compatibility
    import math
    clean_records = [
        {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}
        for row in records
    ]

    t0 = time.perf_counter()
    serialised = json.dumps(clean_records)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 500, f"JSON serialisation took {elapsed_ms:.1f}ms (limit: 500ms)"
    assert len(serialised) > 0


def test_all_8_scenarios_serialise_under_500ms(payloads):
    """All 8 scenarios serialise their tick histories in < 500ms combined."""
    import math

    t0 = time.perf_counter()
    for sc_id, payload in payloads.items():
        records = payload["tick_df"].to_dict(orient="records")
        clean = [
            {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in row.items()}
            for row in records
        ]
        json.dumps(clean)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms < 500, (
        f"All 8 scenarios serialised in {elapsed_ms:.1f}ms (limit: 500ms)"
    )
