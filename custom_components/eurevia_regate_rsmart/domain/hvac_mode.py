"""Aggregate zone HVAC actions for global climate."""

from __future__ import annotations

from typing import Any

from .setpoints import resolve_zone_hvac_action


def aggregate_zone_hvac_action(states: list[dict[str, Any]], *, cooling_active: bool) -> str:
    """Global action from zone states. Heat/cool is a single installation axis (system PAC)."""
    for state in states:
        if state and resolve_zone_hvac_action(state, cooling_active=cooling_active) != "off":
            return "cool" if cooling_active else "heat"
    return "off"
