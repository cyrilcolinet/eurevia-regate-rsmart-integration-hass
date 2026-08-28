"""Aggregate zone HVAC actions for global climate."""

from __future__ import annotations

from typing import Any

from .setpoints import resolve_zone_hvac_action


def aggregate_zone_hvac_action(states: list[dict[str, Any]]) -> str:
    active: list[str] = []
    for state in states:
        if not state:
            continue
        action = resolve_zone_hvac_action(state)
        if action != "off":
            active.append(action)
    if not active:
        return "off"
    if all(action == "heat" for action in active):
        return "heat"
    if all(action == "cool" for action in active):
        return "cool"
    if "heat" in active and "cool" in active:
        return "heat_cool"
    return active[0]
