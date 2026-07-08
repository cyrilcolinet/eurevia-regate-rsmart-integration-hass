"""Sensor platform with auto-discovered terminal and zone fields."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SIGNAL_DISCOVERY_UPDATED,
    SIGNAL_HVAC_DEVICE_STATE_UPDATED,
    SIGNAL_MQTT_CONNECTION_CHANGED,
    SIGNAL_ZONES_UPDATED,
)
from .entity import EureviaRegateEntity, EureviaZoneEntity, bloc_cvc_device_info, zone_device_info
from .lib import resolve_terminal_state
from .lib.entity_discovery import (
    terminal_sensor_specs_for_discovery,
    zone_entity_cache_key,
    zone_sensor_specs_for_zone,
)
from .lib.field_registry import FieldSensorSpec
from .platform_helpers import setup_dynamic_entities, zone_keys_from_store
from .store import get_store


class EureviaRegateConnectivitySensor(EureviaRegateEntity, SensorEntity):
    _attr_translation_key = "connectivity"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["connected", "disconnected"]

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str) -> None:
        super().__init__(hass, entry, entry_id)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_connectivity"

    @property
    def device_info(self):
        return bloc_cvc_device_info(self._entry)

    @property
    def native_value(self) -> str:
        return "connected" if self._store.mqtt_connected else "disconnected"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        last = self._store.last_mqtt_message_at
        return {
            "mqtt_connected": self._store.mqtt_connected,
            "last_mqtt_message_at": last.isoformat() if last else None,
        }


class EureviaRegateTerminalSensor(EureviaRegateEntity, SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        spec: FieldSensorSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self._spec = spec
        self._hvac_unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_terminal_{spec.suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_device_class = spec.device_class
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_state_class = spec.state_class
        if spec.entity_category is not None:
            self._attr_entity_category = spec.entity_category

    @property
    def device_info(self):
        return bloc_cvc_device_info(self._entry)

    @property
    def native_value(self):
        state, _device_id = resolve_terminal_state(self._store.hvac_raw, self._store.discovery)
        if self._spec.value_fn:
            return self._spec.value_fn(state)
        return state.get(self._spec.mqtt_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state, device_id = resolve_terminal_state(self._store.hvac_raw, self._store.discovery)
        out: dict[str, Any] = {}
        if device_id:
            out["read_from_device"] = device_id
        for key in ("Channels_Cmd", "Channels", "Assembly"):
            if key in state:
                out[key.lower()] = state.get(key)
        return out

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        discovery = self._store.discovery
        device_ids = list(discovery.terminal_read_ids) if discovery else []

        @callback
        def _updated(device_id: str) -> None:
            if device_id in device_ids:
                self.async_write_ha_state()

        self._hvac_unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_HVAC_DEVICE_STATE_UPDATED}_{self._entry_id}",
            _updated,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._hvac_unsub:
            self._hvac_unsub()
            self._hvac_unsub = None
        await super().async_will_remove_from_hass()


class EureviaRegateZoneSensor(EureviaZoneEntity, SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        zone_key: str,
        spec: FieldSensorSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id, zone_key)
        self._spec = spec
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_{spec.suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_device_class = spec.device_class
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_state_class = spec.state_class
        if spec.entity_category is not None:
            self._attr_entity_category = spec.entity_category

    @property
    def device_info(self):
        return zone_device_info(self._zone_key, self._zone_cfg)

    @property
    def native_value(self):
        if self._spec.value_fn:
            return self._spec.value_fn(self._zone_state)
        return self._zone_state.get(self._spec.mqtt_key)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = get_store(hass, entry.entry_id)
    added_terminal = store.added("terminal_sensor")
    added_zone = store.added("zone_sensor")

    def build_connectivity() -> list[SensorEntity]:
        if "connectivity" in added_terminal:
            return []
        added_terminal.add("connectivity")
        return [EureviaRegateConnectivitySensor(hass, entry, entry.entry_id)]

    def build_terminal_entities() -> list[SensorEntity]:
        discovery = store.discovery
        if not discovery or not discovery.has_terminal:
            return []
        specs = terminal_sensor_specs_for_discovery(discovery.terminal_keys)
        entities: list[SensorEntity] = []
        for spec in specs:
            if spec.suffix in added_terminal:
                continue
            entities.append(EureviaRegateTerminalSensor(hass, entry, entry.entry_id, spec))
            added_terminal.add(spec.suffix)
        return entities

    def build_zone_entities() -> list[SensorEntity]:
        discovery = store.discovery
        zone_field_keys = discovery.zone_keys if discovery else frozenset()
        entities: list[SensorEntity] = []
        for zone_key in zone_keys_from_store(store):
            zone_state = store.zone_state.get(zone_key) or {}
            for spec in zone_sensor_specs_for_zone(zone_key, zone_state, zone_field_keys):
                entity_key = zone_entity_cache_key(zone_key, spec.suffix)
                if entity_key in added_zone:
                    continue
                entities.append(
                    EureviaRegateZoneSensor(hass, entry, entry.entry_id, zone_key, spec)
                )
                added_zone.add(entity_key)
        return entities

    def build_entities() -> list[SensorEntity]:
        return build_connectivity() + build_terminal_entities() + build_zone_entities()

    setup_dynamic_entities(
        hass,
        entry,
        async_add_entities,
        build_entities,
        (
            SIGNAL_ZONES_UPDATED,
            SIGNAL_DISCOVERY_UPDATED,
            SIGNAL_MQTT_CONNECTION_CHANGED,
        ),
    )
