"""Live MQTT integration tests (manual / secrets only)."""

from __future__ import annotations

import json
import os

import pytest

pytestmark = pytest.mark.integration

HOST = os.getenv("REGATE_MQTT_HOST")
PORT = int(os.getenv("REGATE_MQTT_PORT", "1883"))
PREFIX = os.getenv("REGATE_MQTT_PREFIX", "local")

if not HOST:
    pytest.skip("REGATE_MQTT_HOST not set", allow_module_level=True)


@pytest.fixture(scope="module")
def mqtt_messages():
    import time

    import paho.mqtt.client as mqtt

    messages: dict[str, str] = {}

    def on_connect(client, _userdata, _flags, reason_code, _properties=None):
        assert reason_code == 0
        client.subscribe(f"{PREFIX}/zones")
        client.subscribe(f"{PREFIX}/hvac/devices/+")

    def on_message(_client, _userdata, msg):
        messages.setdefault(msg.topic, msg.payload.decode("utf-8"))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ha-integration-test")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(HOST, PORT, 10)
    client.loop_start()
    time.sleep(5)
    client.loop_stop()
    client.disconnect()
    return messages


def test_zones_topic_returns_climatic_array(mqtt_messages):
    payload = mqtt_messages.get(f"{PREFIX}/zones")
    assert payload is not None
    zones = json.loads(payload)
    assert isinstance(zones, list)
    assert any(zone.get("isClimatic") for zone in zones)


def test_hvac_devices_include_terminal(mqtt_messages):
    terminal = mqtt_messages.get(f"{PREFIX}/hvac/devices/10")
    assert terminal is not None
    data = json.loads(terminal)
    assert "Water_Temp" in data or "Air_Temp" in data
