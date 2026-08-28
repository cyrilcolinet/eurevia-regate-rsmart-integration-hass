"""Tests for zone binary-sensor specs (window / presence)."""

from __future__ import annotations

from eurevia_regate_rsmart.domain.binary_registry import (
    ZONE_BINARY_SPECS,
    zone_binary_specs_for_zone,
)

_BY_SUFFIX = {spec.suffix: spec for spec in ZONE_BINARY_SPECS}
_WINDOW = _BY_SUFFIX["zone_window"]
_PRESENCE = _BY_SUFFIX["zone_presence"]


def test_specs_selected_by_present_keys() -> None:
    assert zone_binary_specs_for_zone({}) == []
    assert [s.suffix for s in zone_binary_specs_for_zone({"Window": False})] == ["zone_window"]
    assert [s.suffix for s in zone_binary_specs_for_zone({"Detection": "Absence"})] == [
        "zone_presence"
    ]
    both = {s.suffix for s in zone_binary_specs_for_zone({"Window": True, "Detection": "Presence"})}
    assert both == {"zone_window", "zone_presence"}


def test_window_value_fn() -> None:
    assert _WINDOW.value_fn({"Window": True}) is True
    assert _WINDOW.value_fn({"Window": False}) is False
    assert _WINDOW.value_fn({}) is None


def test_presence_value_fn() -> None:
    assert _PRESENCE.value_fn({"Detection": "Presence"}) is True
    assert _PRESENCE.value_fn({"Detection": "presence"}) is True
    assert _PRESENCE.value_fn({"Detection": "Absence"}) is False
    assert _PRESENCE.value_fn({}) is None
