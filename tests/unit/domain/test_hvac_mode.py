"""Tests for zone HVAC action aggregation (single installation heat/cool axis)."""

from eurevia_regate_rsmart.domain.hvac_mode import aggregate_zone_hvac_action
from eurevia_regate_rsmart.domain.setpoints import (
    MODE_COMFORT,
    MODE_ECO,
    MODE_OFF,
    resolve_zone_hvac_action,
)


def test_resolve_zone_hvac_action_off():
    assert resolve_zone_hvac_action({"Mode": MODE_OFF}, cooling_active=False) == "off"


def test_resolve_zone_hvac_action_heat():
    assert resolve_zone_hvac_action({"Mode": MODE_COMFORT}, cooling_active=False) == "heat"


def test_aggregate_off_when_all_zones_off():
    zones = [{"Mode": MODE_OFF}, {"Mode": MODE_OFF}]
    assert aggregate_zone_hvac_action(zones, cooling_active=False) == "off"


def test_aggregate_heat_when_any_zone_on_and_not_cooling():
    zones = [{"Mode": MODE_OFF}, {"Mode": MODE_COMFORT}]
    assert aggregate_zone_hvac_action(zones, cooling_active=False) == "heat"


def test_aggregate_cool_when_system_is_cooling():
    zones = [{"Mode": MODE_ECO}, {"Mode": MODE_COMFORT}]
    assert aggregate_zone_hvac_action(zones, cooling_active=True) == "cool"
