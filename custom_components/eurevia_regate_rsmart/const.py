"""Constants for the Eurevia reGATE (rSmart) integration."""

from __future__ import annotations

from typing import Any

DOMAIN = "eurevia_regate_rsmart"
NAME = "Eurevia reGATE (rSmart)"
LOGGER = "custom_components.eurevia_regate_rsmart"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PREFIX = "prefix"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ZONES = "zones"
CONF_COOLING = "cooling"
CONF_TELEMETRY = "telemetry"
CONF_TELEMETRY_ONBOARDING = "telemetry_onboarding_shown"

DEFAULT_PORT = 1883
DEFAULT_PREFIX = "local"
DEFAULT_KEEPALIVE = 30

# Dispatcher signals (suffix with entry_id at runtime)
SIGNAL_ZONES_UPDATED = f"{DOMAIN}_zones_updated"
SIGNAL_ZONE_STATE_UPDATED = f"{DOMAIN}_zone_state_updated"
SIGNAL_HVAC_DEVICE_STATE_UPDATED = f"{DOMAIN}_hvac_device_state_updated"
SIGNAL_DISCOVERY_UPDATED = f"{DOMAIN}_discovery_updated"
SIGNAL_MQTT_CONNECTION_CHANGED = f"{DOMAIN}_mqtt_connection_changed"

MQTT_DISCONNECTED_REPAIR_DELAY_S = 600
MQTT_STALE_THRESHOLD_S = 900
MQTT_STALE_CHECK_INTERVAL_S = 300

TELEMETRY_GITHUB_REPO = "cyrilcolinet/eurevia-regate-rsmart-integration-hass"


def topic_zones(prefix: str) -> str:
    return f"{prefix}/zones"


def topic_info(prefix: str) -> str:
    return f"{prefix}/info"


def topic_zigbee_devices(prefix: str) -> str:
    return f"{prefix}/zigbee/devices"


def topic_hvac_devices(prefix: str) -> str:
    return f"{prefix}/hvac/devices/+"


def topic_hvac_set(prefix: str, hvac_device_id: str) -> str:
    return f"{prefix}/hvac/devices/{hvac_device_id}/set"


def parse_hvac_device_id(topic: str, prefix: str) -> str | None:
    """Extract HVAC device id from `{prefix}/hvac/devices/{id}` (not `/set`)."""
    base = f"{prefix}/hvac/devices/"
    if not topic.startswith(base) or topic.endswith("/set"):
        return None
    return topic[len(base) :]


def parse_hub_info(payload: Any) -> tuple[str | None, str | None, str | None]:
    """Pull (sw_version, serial, model_id) from a retained `{prefix}/info` payload.

    `versionSw` is the hub software version users see; `uid` is the stable
    hardware id (the hex suffix of the box hostname). The `serial` field is a
    `"000000"` placeholder on real units, so it is deliberately ignored.
    """
    if not isinstance(payload, dict):
        return None, None, None

    def _clean(key: str) -> str | None:
        value = payload.get(key)
        if not isinstance(value, str):
            return None
        return value.strip() or None

    return _clean("versionSw"), _clean("uid"), _clean("model")
