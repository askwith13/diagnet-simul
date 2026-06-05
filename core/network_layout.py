"""Network layout helpers — shared by viz layer and app startup.

Reads config/networks.yaml once and returns typed layout data.
Safe to import from app.py, viz/, or tabs/ (not generation-layer code).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from core.models import FacilityLayout

NETWORKS_PATH = Path("config/networks.yaml")


def load_network_layout(
    networks_data: dict,
    network_id: str,
) -> dict[str, FacilityLayout]:
    """Extract display layout for all facilities in one network.

    Args:
        networks_data: Parsed networks.yaml dict.
        network_id: e.g. "NET-A".

    Returns:
        Dict mapping facility_id to FacilityLayout.
    """
    net = networks_data["networks"][network_id]
    return {
        fac_id: FacilityLayout(
            display_name=fac["display_name"],
            type=fac["type"],
            x=float(fac["x"]),
            y=float(fac["y"]),
        )
        for fac_id, fac in net["facilities"].items()
    }


def load_all_layouts(networks_data: dict) -> dict[str, dict[str, FacilityLayout]]:
    """Load layout for all 5 networks.

    Returns:
        Dict mapping network_id -> {facility_id -> FacilityLayout}.
    """
    return {
        net_id: load_network_layout(networks_data, net_id)
        for net_id in networks_data["networks"]
    }


def load_network_links(networks_data: dict, network_id: str) -> list[list]:
    """Return intra-network links as [[src, dst, travel_time_min], ...]."""
    return list(networks_data["networks"][network_id].get("links", []))
