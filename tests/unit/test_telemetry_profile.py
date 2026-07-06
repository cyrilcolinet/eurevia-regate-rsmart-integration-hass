"""Unit tests for telemetry profile helpers."""

from eurevia_regate_rsmart.lib.capabilities import HvacRole, classify_hvac_payload
from eurevia_regate_rsmart.lib.telemetry_profile import (
    is_placeholder_thermostat,
    profile_fingerprint,
    profile_needs_telemetry,
    profile_supported_by_integration,
    unknown_keys_for_profile,
)


def test_thermostat_with_known_keys_is_supported():
    profile = classify_hvac_payload(
        "101",
        {
            "Th_ID": "abc123",
            "Mode": 1,
            "Tmp": 21.0,
            "Stp_Comf": 22.0,
            "Window": False,
        },
    )
    unknown = unknown_keys_for_profile(profile)

    assert unknown == []
    assert profile_supported_by_integration(profile, unknown) is True
    assert profile_needs_telemetry(profile, unknown) is False


def test_system_device_skips_telemetry():
    profile = classify_hvac_payload("0", {"Heating_Mode": 1, "PAC": True, "Mode": 0})
    unknown = unknown_keys_for_profile(profile)

    assert unknown == []
    assert profile_needs_telemetry(profile, unknown) is False
    assert profile_supported_by_integration(profile, unknown) is False


def test_thermostat_with_config_keys_skips_telemetry():
    profile = classify_hvac_payload(
        "101",
        {
            "Th_ID": "abc123",
            "Mode": 1,
            "Tmp": 21.0,
            "Stp_Comf": 22.0,
            "Stp_Comf_Def": 20,
            "Window": False,
        },
    )
    unknown = unknown_keys_for_profile(profile)

    assert unknown == []
    assert profile_needs_telemetry(profile, unknown) is False


def test_unknown_mqtt_key_triggers_telemetry():
    profile = classify_hvac_payload(
        "101",
        {
            "Th_ID": "abc123",
            "Mode": 1,
            "Tmp": 21.0,
            "Stp_Comf": 22.0,
            "Mystery_Field": 42,
        },
    )
    unknown = unknown_keys_for_profile(profile)

    assert unknown == ["Mystery_Field"]
    assert profile_needs_telemetry(profile, unknown) is True


def test_placeholder_thermostat_is_ignored():
    profile = classify_hvac_payload("101", {"Th_ID": "Th_ID", "Mode": 0})
    assert is_placeholder_thermostat(profile, {"101": {"Th_ID": "Th_ID", "Mode": 0}}) is True


def test_fingerprint_is_stable_without_device_id():
    export_a = {
        "roles": ["system"],
        "mqtt_keys": ["Heating_Mode", "PAC"],
        "unknown_keys": [],
    }
    export_b = {
        "roles": ["system"],
        "mqtt_keys": ["PAC", "Heating_Mode"],
        "unknown_keys": [],
    }

    assert profile_fingerprint(export_a) == profile_fingerprint(export_b)


def test_actuator_only_device_needs_telemetry():
    profile = classify_hvac_payload("50", {"Pos_Min": 0, "Pos_Max": 100})
    unknown = unknown_keys_for_profile(profile)

    assert profile.roles & HvacRole.ACTUATOR
    assert profile_needs_telemetry(profile, unknown) is True


def test_terminal_purifier_profile_from_issue_3_is_supported():
    """Full Bloc CVC payload — keys from telemetry issue #3."""
    profile = classify_hvac_payload(
        "10",
        {
            "Absence_Detection_Mode": 0,
            "Absence_Detection_Timer": 30,
            "Actuator_Type": 1,
            "Air_Temp": 21.0,
            "Assembly": 3,
            "Channels": 1,
            "Channels_Bound_Closing": 0,
            "Channels_Bound_Opening": 100,
            "Channels_Cmd": 0,
            "Comm": False,
            "DB": 0.5,
            "Fan_1C": 10,
            "Fan_2C": 20,
            "Fan_3C": 30,
            "Fan_4C": 40,
            "Fan_5C": 50,
            "Fan_6C": 60,
            "Fan_Cmd": 0,
            "Fan_E": 10,
            "Fan_Max": 100,
            "Fan_Min": 0,
            "Fan_Mode": 1,
            "Fan_N": 20,
            "Fan_S": 30,
            "Fan_Speed": 40,
            "Fan_Timer": 15,
            "Hyst": 0.3,
            "Inverter_Min": 5,
            "Inverter_Min_Summer": 10,
            "MTA": 0,
            "Mode": 2,
            "Name": "Terminal",
            "Operating_Mode": 0,
            "Operating_Priority": 1,
            "Operating_authorization": 1,
            "PID_Disabled_OP": 0,
            "PID_Enable": 1,
            "PID_Integral_Default": 0,
            "PID_Max_Interval": 300,
            "PID_Prop_Band": 2.0,
            "PID_Smooth_Factor": 0.5,
            "PID_T_Derivate": 60,
            "PID_T_Integral": 120,
            "P_Fan_E": 0,
            "P_Fan_N": 0,
            "P_Fan_S": 0,
            "P_Mode": 0,
            "P_Timer": 0,
            "P_Timer_Def": 60,
            "P_Timer_Max": 120,
            "Presence_Detection_Timer": 10,
            "Stp_AF": 10,
            "Test_Aeraulic": 0,
            "Test_Config": 0,
            "Test_Fan": 0,
            "Test_Fan_M": 0,
            "Test_Speed": 0,
            "Test_V1": 0,
            "Test_V2": 0,
            "Type": 1,
            "Valve_Cmd": 50,
            "Valve_Cmd_Corrected": 48,
            "Valve_Debugging_Timer": 0,
            "Valve_Heat_Debugging_Timer": 0,
            "Valve_PWM_Timer": 0,
            "Valve_Type": 2,
            "Water_Auth": True,
            "Water_Cold": 15.0,
            "Water_Hot": 35.0,
            "Water_Temp": 22.0,
            "Window_Close_Timer": 5,
            "Window_Open_Mode": 1,
            "Window_Open_Timer": 10,
            "Z_Min_Reference_Capacity_Authorize": 0,
            "Z_Step_Speed_2": 25,
            "Z_Step_Speed_3": 50,
            "Z_Step_Speed_4": 75,
            "Z_Temp_Limit_Speed_1": 18.0,
            "Z_Temp_Limit_Speed_2": 22.0,
            "Z_brand": 0,
        },
    )
    unknown = unknown_keys_for_profile(profile)

    assert unknown == []
    assert profile_supported_by_integration(profile, unknown) is True
    assert profile_needs_telemetry(profile, unknown) is False
