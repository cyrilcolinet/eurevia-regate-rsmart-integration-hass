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
