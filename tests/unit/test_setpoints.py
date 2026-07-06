"""Unit tests for zone setpoint resolution."""

from eurevia_regate_rsmart.lib.setpoints import (
    MODE_COMFORT,
    MODE_ECO,
    MODE_OFF,
    MODE_REDUCED,
    is_heating_active,
    read_active_setpoint,
    setpoint_key_for_mode,
    write_setpoint_payload,
)


def test_setpoint_key_for_mode_comfort():
    assert setpoint_key_for_mode(MODE_COMFORT, heating=True) == "Stp_Comf"
    assert setpoint_key_for_mode(MODE_ECO, heating=True) == "Stp_Eco_H"
    assert setpoint_key_for_mode(MODE_ECO, heating=False) == "Stp_Eco_C"
    assert setpoint_key_for_mode(MODE_REDUCED, heating=True) == "Stp_Reduc_H"
    assert setpoint_key_for_mode(MODE_OFF, heating=True) is None


def test_is_heating_active_from_demand():
    assert is_heating_active({"Demand": True}) is True
    assert is_heating_active({"Demand": False, "Tmp": 28.0, "Stp_Comf": 21.0}) is False
    assert is_heating_active({"Demand": False, "Tmp": 19.0, "Stp_Comf": 21.0}) is True


def test_read_active_setpoint_eco_heating():
    state = {
        "Mode": MODE_ECO,
        "Tmp": 19.0,
        "Stp_Comf": 21.0,
        "Stp_Eco_H": 16.0,
        "Stp_Eco_C": 25.0,
        "Demand": False,
    }
    assert read_active_setpoint(state) == 16.0


def test_read_active_setpoint_eco_cooling():
    state = {
        "Mode": MODE_ECO,
        "Tmp": 28.0,
        "Stp_Comf": 21.0,
        "Stp_Eco_H": 16.0,
        "Stp_Eco_C": 25.0,
        "Demand": False,
    }
    assert read_active_setpoint(state) == 25.0


def test_write_setpoint_payload_keeps_eco_mode():
    state = {
        "Mode": MODE_ECO,
        "Tmp": 28.0,
        "Stp_Comf": 21.0,
        "Demand": False,
    }
    payload = write_setpoint_payload(state, 24.0)
    assert payload == {"Stp_Eco_C": 24.0, "Mode": MODE_ECO}


def test_write_setpoint_payload_comfort():
    state = {"Mode": MODE_COMFORT, "Tmp": 21.0, "Stp_Comf": 21.0}
    payload = write_setpoint_payload(state, 20.5)
    assert payload == {"Stp_Comf": 20.5, "Mode": MODE_COMFORT}
