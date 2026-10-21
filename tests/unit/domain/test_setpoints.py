"""Unit tests for zone setpoint resolution."""

from eurevia_regate_rsmart.domain.setpoints import (
    MODE_COMFORT,
    MODE_ECO,
    MODE_OFF,
    MODE_REDUCED,
    read_active_setpoint,
    resolve_zone_hvac_action,
    setpoint_key_for_mode,
    write_setpoint_payload,
)

# Real Séjour payload (wired thermostat, room warmer than setpoint): the old
# temperature heuristic mislabelled this "cool"; the axis now comes from the
# system PAC value, not Tmp vs Stp_Comf.
SEJOUR = {"Mode": MODE_ECO, "Demand": False, "Tmp": 21.6, "Stp_Comf": 21.0}


def test_setpoint_key_for_mode_comfort():
    assert setpoint_key_for_mode(MODE_COMFORT, heating=True) == "Stp_Comf"
    assert setpoint_key_for_mode(MODE_ECO, heating=True) == "Stp_Eco_H"
    assert setpoint_key_for_mode(MODE_ECO, heating=False) == "Stp_Eco_C"
    assert setpoint_key_for_mode(MODE_REDUCED, heating=True) == "Stp_Reduc_H"
    assert setpoint_key_for_mode(MODE_OFF, heating=True) is None


def test_read_active_setpoint_eco_heating():
    state = {"Mode": MODE_ECO, "Stp_Eco_H": 16.0, "Stp_Eco_C": 25.0}
    assert read_active_setpoint(state, cooling_active=False) == 16.0


def test_read_active_setpoint_eco_cooling():
    state = {"Mode": MODE_ECO, "Stp_Eco_H": 16.0, "Stp_Eco_C": 25.0}
    assert read_active_setpoint(state, cooling_active=True) == 25.0


def test_read_active_setpoint_warm_room_stays_heating():
    # Room above setpoint must not flip to the cooling setpoint when not cooling.
    state = {**SEJOUR, "Stp_Eco_H": 16.0, "Stp_Eco_C": 25.0}
    assert read_active_setpoint(state, cooling_active=False) == 16.0


def test_write_setpoint_payload_cooling_eco():
    state = {"Mode": MODE_ECO}
    payload = write_setpoint_payload(state, 24.0, cooling_active=True)
    assert payload == {"Stp_Eco_C": 24.0, "Mode": MODE_ECO}


def test_write_setpoint_payload_heating_eco():
    state = {"Mode": MODE_ECO}
    payload = write_setpoint_payload(state, 17.0, cooling_active=False)
    assert payload == {"Stp_Eco_H": 17.0, "Mode": MODE_ECO}


def test_write_setpoint_payload_comfort():
    state = {"Mode": MODE_COMFORT}
    payload = write_setpoint_payload(state, 20.5, cooling_active=False)
    assert payload == {"Stp_Comf": 20.5, "Mode": MODE_COMFORT}


def test_resolve_zone_hvac_action_heating_when_warm():
    # The reported action follows the installation axis, not temperature.
    assert resolve_zone_hvac_action(SEJOUR, cooling_active=False) == "heat"


def test_resolve_zone_hvac_action_cooling():
    assert resolve_zone_hvac_action({"Mode": MODE_COMFORT}, cooling_active=True) == "cool"


def test_resolve_zone_hvac_action_off():
    assert resolve_zone_hvac_action({"Mode": MODE_OFF}, cooling_active=True) == "off"
