"""Typed runtime store for a config entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .domain.capabilities import HvacDiscovery, discover_hvac_devices
from .domain.system_registry import COOLING_PAC_VALUE
from .lib.conversion import as_int
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
    pac_handler: bool = False
    cooling_option: bool = False
    telemetry: Any = None
    hub_sw_version: str | None = None
    hub_serial: str | None = None
    hub_model_id: str | None = None
    mqtt_connected: bool = False
    mqtt_disconnect_notified: bool = False
    last_mqtt_message_at: datetime | None = None
    mqtt_disconnect_repair_unsub: Any = None
    mqtt_stale_check_unsub: Any = None
    added_entities: dict[str, set[str]] = field(default_factory=dict)
    purifier_entity_added: bool = False
    climate_global_added: bool = False

    def added(self, platform_key: str) -> set[str]:
        return self.added_entities.setdefault(platform_key, set())

    @property
    def cooling_supported(self) -> bool:
        """Whether this installation can cool (reversible PAC or manual override)."""
        return self.pac_handler or self.cooling_option

    @property
    def cooling_active(self) -> bool:
        """Current heat/cool axis, read back from the system device PAC value."""
        system_id = self.discovery.system_id
        if not system_id:
            return False
        payload = self.hvac_raw.get(system_id) or {}
        return as_int(payload.get("PAC")) == COOLING_PAC_VALUE


def cancel_scheduled_checks(store: RegateStore) -> None:
    if store.mqtt_disconnect_repair_unsub:
        store.mqtt_disconnect_repair_unsub()
        store.mqtt_disconnect_repair_unsub = None
    if store.mqtt_stale_check_unsub:
        store.mqtt_stale_check_unsub()
        store.mqtt_stale_check_unsub = None


def get_store(entry: ConfigEntry) -> RegateStore | None:
    return getattr(entry, "runtime_data", None)
