"""Tests for HVAC auto-discovery from payload patterns."""

from eurevia_regate_rsmart.lib.capabilities import (
    HvacRole,
    classify_hvac_payload,
    discover_hvac_devices,
    resolve_purifier_state,
    resolve_terminal_state,
)

TERMINAL_10 = {
    "Water_Temp": 29.5,
    "Air_Temp": 29.2,
    "Valve_Cmd": 0,
    "Assembly": 3,
    "Fan_Speed": 0,
    "P_Mode": 0,
}

TERMINAL_20 = {
    "Assembly": 1,
    "P_Mode": 2,
    "Water_Auth": True,
}

THERMO_102 = {
    "Mode": 0,
    "Stp_Comf": 20,
    "Tmp": 26.8,
    "Th_ID": "0xcafebabe11111111",
    "RH": 52,
}

PLACEHOLDER_104 = {
    "Mode": 0,
    "Stp_Comf": 22,
    "Tmp": 20,
    "Th_ID": "Th_ID",
}

SYSTEM_0 = {"Mode": 0, "Heating_Mode": 0, "PAC": 0, "Comm": False}

ACTUATOR_11 = {"Pos_Min": 0, "Pos_Max": 100, "Window": "Close", "Detection": "Presence"}


def test_classify_terminal_and_purifier():
    profile = classify_hvac_payload("10", TERMINAL_10)
    assert profile.roles & HvacRole.TERMINAL
    assert profile.roles & HvacRole.PURIFIER
    assert not profile.roles & HvacRole.THERMOSTAT


def test_classify_thermostat_rejects_placeholder():
    profile = classify_hvac_payload("104", PLACEHOLDER_104)
    assert not profile.roles & HvacRole.THERMOSTAT


def test_classify_live_thermostat():
    profile = classify_hvac_payload("102", THERMO_102)
    assert profile.roles & HvacRole.THERMOSTAT


def test_discover_selects_primary_terminal_and_purifier_command():
    hvac_raw = {"10": TERMINAL_10, "20": TERMINAL_20, "102": THERMO_102}
    discovery = discover_hvac_devices(hvac_raw, {"chambre": THERMO_102})
    assert discovery.terminal_primary_id == "10"
    assert discovery.purifier_command_id == "10"
    assert discovery.terminal_read_ids == ("10", "20")
    assert "102" in discovery.thermostat_ids
    assert "RH" in discovery.zone_keys


def test_resolve_terminal_and_purifier_state():
    hvac_raw = {"10": TERMINAL_10, "20": TERMINAL_20}
    discovery = discover_hvac_devices(hvac_raw)
    state, device_id = resolve_terminal_state(hvac_raw, discovery)
    assert device_id == "10"
    assert state["Water_Temp"] == 29.5
    purifier_state, purifier_id = resolve_purifier_state(hvac_raw, discovery)
    assert purifier_id == "10"
    assert purifier_state["P_Mode"] == 0


def test_discover_system_and_actuator():
    hvac_raw = {"0": SYSTEM_0, "11": ACTUATOR_11}
    discovery = discover_hvac_devices(hvac_raw)
    assert discovery.system_id == "0"
    assert "11" in discovery.actuator_ids
