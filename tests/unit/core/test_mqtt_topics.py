"""Tests for MQTT topic helpers."""

from eurevia_regate_rsmart.const import (
    parse_hub_info,
    parse_hvac_device_id,
    topic_hvac_devices,
    topic_hvac_set,
    topic_info,
    topic_zigbee_devices,
    topic_zones,
)


def test_topic_helpers_use_prefix():
    assert topic_zones("local") == "local/zones"
    assert topic_zigbee_devices("local") == "local/zigbee/devices"
    assert topic_hvac_devices("local") == "local/hvac/devices/+"
    assert topic_hvac_set("local", "10") == "local/hvac/devices/10/set"
    assert topic_info("local") == "local/info"


def test_parse_hub_info():
    payload = {
        "uid": "0D3CA209DAB57DE4",
        "serial": "000000",
        "versionSw": "4.0.21",
        "model": "EUR0800009A",
    }
    assert parse_hub_info(payload) == ("4.0.21", "0D3CA209DAB57DE4", "EUR0800009A")
    # Missing/blank fields and non-dict payloads degrade to None, never the
    # "000000" serial placeholder.
    assert parse_hub_info({}) == (None, None, None)
    assert parse_hub_info({"uid": "  ", "versionSw": None}) == (None, None, None)
    assert parse_hub_info("not-a-dict") == (None, None, None)


def test_parse_hvac_device_id():
    assert parse_hvac_device_id("local/hvac/devices/101", "local") == "101"
    assert parse_hvac_device_id("local/hvac/devices/101/set", "local") is None
    assert parse_hvac_device_id("other/topic", "local") is None
