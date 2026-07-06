"""Sensor platform with auto-discovered terminal and zone fields."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SIGNAL_DISCOVERY_UPDATED,
    SIGNAL_HVAC_DEVICE_STATE_UPDATED,
    SIGNAL_ZONE_STATE_UPDATED,
    SIGNAL_ZONES_UPDATED,
)
from .entity import EureviaRegateEntity, bloc_cvc_device_info, zone_device_info
from .lib import resolve_terminal_state
from .lib.field_registry import FieldSensorSpec, terminal_specs_for_keys, zone_specs_for_keys


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
        self._unsub = None
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
        state, _device_id = resolve_terminal_state(
            self._store.get("hvac_raw") or {},
            self._store.get("discovery"),
        )
        if self._spec.value_fn:
            return self._spec.value_fn(state)
        return state.get(self._spec.mqtt_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state, device_id = resolve_terminal_state(
            self._store.get("hvac_raw") or {},
            self._store.get("discovery"),
        )
        out: dict[str, Any] = {}
        if device_id:
            out["read_from_device"] = device_id
        for key in ("Channels_Cmd", "Channels", "Assembly"):
            if key in state:
                out[key.lower()] = state.get(key)
        return out

    async def async_added_to_hass(self) -> None:
        discovery = self._store.get("discovery")
        device_ids = list(discovery.terminal_read_ids) if discovery else []

        @callback
        def _updated(device_id: str) -> None:
            if device_id in device_ids:
                self.async_write_ha_state()

        self._unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_HVAC_DEVICE_STATE_UPDATED}_{self._entry_id}",
            _updated,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None


class EureviaRegateZoneSensor(EureviaRegateEntity, SensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        zone_key: str,
        spec: FieldSensorSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self._zone_key = zone_key
        self._spec = spec
        self._unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_{spec.suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_device_class = spec.device_class
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_state_class = spec.state_class
        if spec.entity_category is not None:
            self._attr_entity_category = spec.entity_category

    @property
    def _zone_cfg(self) -> dict:
        return (self._store.get("zone_cfg") or {}).get(self._zone_key, {}) or {}

    @property
    def _zone_state(self) -> dict:
        return (self._store.get("zone_state") or {}).get(self._zone_key, {}) or {}

    @property
    def device_info(self):
        return zone_device_info(self._zone_key, self._zone_cfg)

    @property
    def native_value(self):
        if self._spec.value_fn:
            return self._spec.value_fn(self._zone_state)
        return self._zone_state.get(self._spec.mqtt_key)

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(zone_key: str) -> None:
            if zone_key == self._zone_key:
                self.async_write_ha_state()

        self._unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_ZONE_STATE_UPDATED}_{self._entry_id}",
            _updated,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    added_terminal: set[str] = store.setdefault("added_terminal_sensor_keys", set())
    added_zone_keys: set[str] = store.setdefault("added_zone_sensor_keys", set())

    def zone_keys() -> list[str]:
        return list((store.get("zone_cfg") or {}).keys())

    def build_terminal_entities() -> list[SensorEntity]:
        discovery = store.get("discovery")
        if not discovery or not discovery.has_terminal:
            return []
        specs = terminal_specs_for_keys(discovery.terminal_keys)
        entities: list[SensorEntity] = []
        for spec in specs:
            if spec.suffix in added_terminal:
                continue
            entities.append(EureviaRegateTerminalSensor(hass, entry, entry.entry_id, spec))
            added_terminal.add(spec.suffix)
        return entities

    def build_zone_entities() -> list[SensorEntity]:
        discovery = store.get("discovery")
        zone_field_keys = discovery.zone_keys if discovery else frozenset()
        specs = zone_specs_for_keys(zone_field_keys)
        entities: list[SensorEntity] = []
        for zone_key in zone_keys():
            zone_state = (store.get("zone_state") or {}).get(zone_key) or {}
            active_specs = [spec for spec in specs if spec.mqtt_key in zone_state]
            if not active_specs:
                active_specs = specs
            for spec in active_specs:
                entity_key = f"{zone_key}:{spec.suffix}"
                if entity_key in added_zone_keys:
                    continue
                entities.append(
                    EureviaRegateZoneSensor(hass, entry, entry.entry_id, zone_key, spec)
                )
                added_zone_keys.add(entity_key)
        return entities

    async_add_entities(build_terminal_entities() + build_zone_entities(), update_before_add=False)

    @callback
    def _zones_updated() -> None:
        async_add_entities(build_zone_entities(), update_before_add=False)

    @callback
    def _discovery_updated() -> None:
        async_add_entities(
            build_terminal_entities() + build_zone_entities(),
            update_before_add=False,
        )

    entry.async_on_unload(
        async_dispatcher_connect(hass, f"{SIGNAL_ZONES_UPDATED}_{entry.entry_id}", _zones_updated)
    )
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{SIGNAL_DISCOVERY_UPDATED}_{entry.entry_id}", _discovery_updated
        )
    )
