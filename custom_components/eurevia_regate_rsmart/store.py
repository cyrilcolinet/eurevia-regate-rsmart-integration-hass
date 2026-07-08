"""Typed runtime store for a config entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .lib.capabilities import HvacDiscovery, discover_hvac_devices
from .mqtt import SimpleMqttClient


@dataclass
class RegateStore:
    """MQTT state, zone mappings, and dynamic-entity bookkeeping for one entry."""

    prefix: str
    client: SimpleMqttClient | None = None
    zones_raw: list[dict[str, Any]] = field(default_factory=list)
    zigbee_raw: list[dict[str, Any]] | None = None
    hvac_raw: dict[str, dict[str, Any]] = field(default_factory=dict)
    hvac_id_to_th_id: dict[str, str] = field(default_factory=dict)
    zone_cfg: dict[str, dict[str, Any]] = field(default_factory=dict)
    th_id_to_zone_key: dict[str, str] = field(default_factory=dict)
    zone_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    zone_key_to_hvac_id: dict[str, str] = field(default_factory=dict)
    discovery: HvacDiscovery = field(default_factory=lambda: discover_hvac_devices({}))
    telemetry: Any = None
    mqtt_connected: bool = False
    mqtt_disconnect_notified: bool = False
    last_mqtt_message_at: datetime | None = None
    added_entities: dict[str, set[str]] = field(default_factory=dict)
    purifier_entity_added: bool = False
    climate_global_added: bool = False

    def added(self, platform_key: str) -> set[str]:
        return self.added_entities.setdefault(platform_key, set())


def get_store(hass: HomeAssistant, entry_id: str) -> RegateStore:
    return hass.data[DOMAIN][entry_id]
