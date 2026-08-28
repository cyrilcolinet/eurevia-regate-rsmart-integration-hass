"""Tests for zone binary-sensor specs (window / presence)."""

from __future__ import annotations

from eurevia_regate_rsmart.domain.binary_registry import (
    ZONE_BINARY_SPECS,
    zone_binary_specs_for_zone,
)

_BY_SUFFIX = {spec.suffix: spec for spec in ZONE_BINARY_SPECS}
_WINDOW = _BY_SUFFIX["zone_window"]


def test_specs_selected_by_present_keys() -> None:
    assert zone_binary_specs_for_zone({}) == []
    assert [s.suffix for s in zone_binary_specs_for_zone({"Window": False})] == ["zone_window"]
    assert zone_binary_specs_for_zone({"Detection": "Absence"}) == []


def test_window_value_fn() -> None:
    assert _WINDOW.value_fn({"Window": True}) is True
    assert _WINDOW.value_fn({"Window": False}) is False
    assert _WINDOW.value_fn({}) is None
