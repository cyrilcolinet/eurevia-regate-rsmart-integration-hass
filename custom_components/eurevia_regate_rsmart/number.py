"""Number platform for writable zone setpoints discovered from MQTT."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SIGNAL_DISCOVERY_UPDATED,
    SIGNAL_ZONE_STATE_UPDATED,
    SIGNAL_ZONES_UPDATED,
    topic_hvac_set,
)
from .entity import EureviaRegateEntity, zone_device_info
from .lib import as_float
from .lib.setpoint_registry import SetpointNumberSpec, setpoint_specs_for_keys


class EureviaRegateZoneSetpointNumber(EureviaRegateEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        zone_key: str,
        spec: SetpointNumberSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self._zone_key = zone_key
        self._spec = spec
        self._unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_{spec.suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_native_step = spec.step
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
    def native_value(self) -> float | None:
        return as_float(self._zone_state.get(self._spec.mqtt_key))

    @property
    def native_min_value(self) -> float:
        if self._spec.mqtt_key == "Stp_Comf":
            value = as_float(self._zone_state.get("Stp_Comf_Min"))
            if value is not None:
                return value
        return 5.0

    @property
    def native_max_value(self) -> float:
        if self._spec.mqtt_key == "Stp_Comf":
            value = as_float(self._zone_state.get("Stp_Comf_Max"))
            if value is not None:
                return value
        return 35.0

    async def async_set_native_value(self, value: float) -> None:
        hvac_id = (self._store.get("zone_key_to_hvac_id") or {}).get(self._zone_key)
        if not hvac_id:
            return
        topic = topic_hvac_set(self._store["prefix"], hvac_id)
        payload: dict[str, Any] = {self._spec.mqtt_key: float(value)}
        await self._store["client"].publish(topic, json.dumps(payload).encode("utf-8"))

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
    added: set[str] = store.setdefault("added_zone_number_keys", set())

    def zone_keys() -> list[str]:
        return list((store.get("zone_cfg") or {}).keys())

    def build_entities() -> list[NumberEntity]:
        discovery = store.get("discovery")
        zone_field_keys = discovery.zone_keys if discovery else frozenset()
        specs = setpoint_specs_for_keys(zone_field_keys)
        entities: list[NumberEntity] = []
        for zone_key in zone_keys():
            zone_state = (store.get("zone_state") or {}).get(zone_key) or {}
            for spec in specs:
                if spec.mqtt_key not in zone_state:
                    continue
                entity_key = f"{zone_key}:{spec.suffix}"
                if entity_key in added:
                    continue
                entities.append(
                    EureviaRegateZoneSetpointNumber(hass, entry, entry.entry_id, zone_key, spec)
                )
                added.add(entity_key)
        return entities

    async_add_entities(build_entities(), update_before_add=False)

    @callback
    def _zones_updated() -> None:
        async_add_entities(build_entities(), update_before_add=False)

    @callback
    def _discovery_updated() -> None:
        async_add_entities(build_entities(), update_before_add=False)

    entry.async_on_unload(
        async_dispatcher_connect(hass, f"{SIGNAL_ZONES_UPDATED}_{entry.entry_id}", _zones_updated)
    )
    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{SIGNAL_DISCOVERY_UPDATED}_{entry.entry_id}", _discovery_updated
        )
    )
