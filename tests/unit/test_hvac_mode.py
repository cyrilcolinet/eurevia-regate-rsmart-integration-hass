"""Tests for zone HVAC action resolution."""

from eurevia_regate_rsmart.lib.hvac_mode import aggregate_zone_hvac_action
from eurevia_regate_rsmart.lib.setpoints import (
    MODE_COMFORT,
    MODE_ECO,
    MODE_OFF,
    resolve_zone_hvac_action,
    zone_supports_cooling,
)


def test_resolve_zone_hvac_action_off():
    assert resolve_zone_hvac_action({"Mode": MODE_OFF, "Tmp": 21.0}) == "off"


def test_resolve_zone_hvac_action_heat_from_demand():
    assert resolve_zone_hvac_action({"Mode": MODE_COMFORT, "Demand": True}) == "heat"


def test_resolve_zone_hvac_action_cool_from_temperature():
    state = {
        "Mode": MODE_ECO,
        "Demand": False,
        "Tmp": 28.0,
        "Stp_Comf": 21.0,
        "Stp_Eco_C": 25.0,
    }
    assert resolve_zone_hvac_action(state) == "cool"


def test_aggregate_zone_hvac_action_mixed():
    heat_zone = {"Mode": MODE_COMFORT, "Demand": True}
    cool_zone = {
        "Mode": MODE_ECO,
        "Demand": False,
        "Tmp": 28.0,
        "Stp_Comf": 21.0,
    }
    assert aggregate_zone_hvac_action([heat_zone, cool_zone]) == "heat_cool"


def test_zone_supports_cooling_from_setpoints():
    assert zone_supports_cooling({}, frozenset({"Stp_Eco_C"})) is True
    assert zone_supports_cooling({}, frozenset({"Stp_Comf"})) is False
