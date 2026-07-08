"""Tests for entity discovery rules."""

from eurevia_regate_rsmart.lib.entity_discovery import (
    zone_entity_cache_key,
    zone_number_specs_for_zone,
    zone_sensor_specs_for_zone,
)


def test_zone_entity_cache_key_format():
    assert zone_entity_cache_key("zone_alpha", "stp_comf") == "zone_alpha:stp_comf"


def test_zone_sensor_specs_require_key_in_zone_state():
    zone_state = {"RH": 50, "Tmp": 21.0}
    specs = zone_sensor_specs_for_zone("zone_alpha", zone_state, frozenset({"RH", "Tmp", "Window"}))
    mqtt_keys = {spec.mqtt_key for spec in specs}
    assert mqtt_keys == {"RH"}
    assert "Window" not in mqtt_keys


def test_zone_number_specs_require_key_in_zone_state():
    zone_state = {"Stp_Comf": 20.0}
    specs = zone_number_specs_for_zone(
        "zone_alpha",
        zone_state,
        frozenset({"Stp_Comf", "Stp_Eco_C"}),
    )
    assert [spec.mqtt_key for spec in specs] == ["Stp_Comf"]
