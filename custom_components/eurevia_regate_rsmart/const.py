"""Constants for the Eurevia reGATE (rSmart) integration."""

from __future__ import annotations

DOMAIN = "eurevia_regate_rsmart"
NAME = "Eurevia reGATE (rSmart)"
LOGGER = "custom_components.eurevia_regate_rsmart"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_PREFIX = "prefix"
CONF_ZONES = "zones"
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

TELEMETRY_GITHUB_REPO = "cyrilcolinet/eurevia-regate-rsmart-integration-hass"
TELEMETRY_ISSUE_LABELS = ("device-telemetry",)


def topic_zones(prefix: str) -> str:
    return f"{prefix}/zones"


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
