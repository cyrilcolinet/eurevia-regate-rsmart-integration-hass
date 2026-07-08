"""Tests for system device number specs."""

from eurevia_regate_rsmart.lib.system_registry import (
    COOLING_PAC_VALUE,
    HEATING_PAC_VALUE,
    system_number_specs_for_keys,
)


def test_system_number_specs_only_for_present_keys():
    specs = system_number_specs_for_keys({"Heating_Mode", "PAC", "Comm"})
    assert [spec.mqtt_key for spec in specs] == ["Heating_Mode", "PAC"]


def test_pac_command_values():
    assert HEATING_PAC_VALUE == 0
    assert COOLING_PAC_VALUE == 1
