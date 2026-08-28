"""Tests for MQTT topic helpers."""

from eurevia_regate_rsmart.const import (
    parse_hvac_device_id,
    topic_hvac_devices,
    topic_hvac_set,
    topic_zigbee_devices,
    topic_zones,
)


def test_topic_helpers_use_prefix():
    assert topic_zones("local") == "local/zones"
    assert topic_zigbee_devices("local") == "local/zigbee/devices"
    assert topic_hvac_devices("local") == "local/hvac/devices/+"
    assert topic_hvac_set("local", "10") == "local/hvac/devices/10/set"


def test_parse_hvac_device_id():
    assert parse_hvac_device_id("local/hvac/devices/101", "local") == "101"
    assert parse_hvac_device_id("local/hvac/devices/101/set", "local") is None
    assert parse_hvac_device_id("other/topic", "local") is None
