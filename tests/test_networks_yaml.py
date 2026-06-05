"""Tests for config/networks.yaml — 59-facility network topology."""
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from core.models import FacilityState

NETWORKS_PATH = Path("config/networks.yaml")
FACILITY_STATE_FIELDS = {f.name for f in fields(FacilityState)}
EXPECTED_COUNTS = {"NET-A": 14, "NET-B": 11, "NET-C": 13, "NET-D": 9, "NET-E": 12}
VALID_TYPES = {"hub", "truenat", "microscopy", "chc"}


@pytest.fixture(scope="module")
def networks_data() -> dict:
    return yaml.safe_load(NETWORKS_PATH.read_text())


def test_networks_yaml_loads(networks_data):
    assert isinstance(networks_data, dict)


def test_five_networks_present(networks_data):
    assert set(networks_data["networks"].keys()) == set(EXPECTED_COUNTS.keys())


def test_facility_counts(networks_data):
    for net_id, expected in EXPECTED_COUNTS.items():
        actual = len(networks_data["networks"][net_id]["facilities"])
        assert actual == expected, (
            f"{net_id}: expected {expected} facilities, got {actual}"
        )


def test_total_59_facilities(networks_data):
    total = sum(
        len(net["facilities"]) for net in networks_data["networks"].values()
    )
    assert total == 59, f"Expected 59 total facilities, got {total}"


def test_each_network_has_exactly_one_hub(networks_data):
    for net_id, net in networks_data["networks"].items():
        hubs = [
            f_id for f_id, f in net["facilities"].items()
            if f["type"] == "hub"
        ]
        assert len(hubs) == 1, f"{net_id}: expected 1 hub, got {hubs}"


def test_all_facility_types_valid(networks_data):
    for net_id, net in networks_data["networks"].items():
        for f_id, facility in net["facilities"].items():
            assert facility["type"] in VALID_TYPES, (
                f"{net_id}/{f_id}: unknown type '{facility['type']}'"
            )


def test_every_facility_has_required_keys(networks_data):
    required = {"display_name", "type", "x", "y", "baseline", "thresholds"}
    for net_id, net in networks_data["networks"].items():
        for f_id, facility in net["facilities"].items():
            missing = required - set(facility.keys())
            assert not missing, (
                f"{net_id}/{f_id} missing required keys: {missing}"
            )


def test_every_baseline_has_all_17_facility_state_fields(networks_data):
    for net_id, net in networks_data["networks"].items():
        for f_id, facility in net["facilities"].items():
            baseline_keys = set(facility["baseline"].keys())
            missing = FACILITY_STATE_FIELDS - baseline_keys
            assert not missing, (
                f"{net_id}/{f_id} baseline missing FacilityState fields: {missing}"
            )


def test_canvas_positions_in_unit_range(networks_data):
    for net_id, net in networks_data["networks"].items():
        for f_id, facility in net["facilities"].items():
            x, y = facility["x"], facility["y"]
            assert 0.0 <= x <= 1.0, f"{net_id}/{f_id}: x={x} out of [0,1]"
            assert 0.0 <= y <= 1.0, f"{net_id}/{f_id}: y={y} out of [0,1]"


def test_links_reference_valid_facilities(networks_data):
    for net_id, net in networks_data["networks"].items():
        facility_ids = set(net["facilities"].keys())
        for link in net.get("links", []):
            src, dst, _ = link
            assert src in facility_ids, (
                f"{net_id}: link source '{src}' not a valid facility"
            )
            assert dst in facility_ids, (
                f"{net_id}: link destination '{dst}' not a valid facility"
            )


def test_links_have_positive_travel_times(networks_data):
    for net_id, net in networks_data["networks"].items():
        for link in net.get("links", []):
            src, dst, travel_time = link
            assert travel_time > 0, (
                f"{net_id}: link {src}→{dst} has non-positive travel time {travel_time}"
            )


def test_three_inter_network_links(networks_data):
    links = networks_data.get("inter_network_links", [])
    assert len(links) == 3, f"Expected 3 inter-network links, got {len(links)}"


def test_inter_network_link_keys(networks_data):
    required = {"source", "target", "source_facility", "target_facility",
                "travel_time_min", "flow_type"}
    for link in networks_data["inter_network_links"]:
        missing = required - set(link.keys())
        assert not missing, f"Inter-network link missing keys: {missing}"


def test_inter_network_link_networks_valid(networks_data):
    net_ids = set(networks_data["networks"].keys())
    for link in networks_data["inter_network_links"]:
        assert link["source"] in net_ids, f"Unknown source network: {link['source']}"
        assert link["target"] in net_ids, f"Unknown target network: {link['target']}"


def test_dhc_d_is_net_d_hub(networks_data):
    """DHC-D must be the hub of NET-D (required by architecture inter_network_links)."""
    assert "DHC-D" in networks_data["networks"]["NET-D"]["facilities"]
    assert networks_data["networks"]["NET-D"]["facilities"]["DHC-D"]["type"] == "hub"


def test_net_d_to_net_a_overflow_link(networks_data):
    """NET-D → NET-A overflow link must exist (architecture requirement)."""
    links = networks_data["inter_network_links"]
    overflow = [
        l for l in links
        if l["source"] == "NET-D" and l["target"] == "NET-A"
        and l["flow_type"] == "overflow"
    ]
    assert len(overflow) == 1, "Missing NET-D → NET-A overflow inter-network link"
