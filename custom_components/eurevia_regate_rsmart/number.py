"""Number platform for writable zone setpoints discovered from MQTT."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY_UPDATED, SIGNAL_ZONES_UPDATED
from .entity import EureviaZoneEntity, async_publish_hvac_command, zone_device_info
from .lib import as_float
from .lib.entity_discovery import zone_entity_cache_key, zone_number_specs_for_zone
from .lib.setpoint_registry import SetpointNumberSpec
from .platform_helpers import setup_dynamic_entities, zone_keys_from_store
from .store import get_store


class EureviaRegateZoneSetpointNumber(EureviaZoneEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        zone_key: str,
        spec: SetpointNumberSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id, zone_key)
        self._spec = spec
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_{spec.suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_native_step = spec.step
        if spec.entity_category is not None:
            self._attr_entity_category = spec.entity_category

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
        hvac_id = self._store.zone_key_to_hvac_id.get(self._zone_key)
        await async_publish_hvac_command(
            self._store,
            str(hvac_id) if hvac_id else "",
            {self._spec.mqtt_key: float(value)},
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = get_store(hass, entry.entry_id)
    added = store.added("number")

    def build_entities() -> list[NumberEntity]:
        discovery = store.discovery
        zone_field_keys = discovery.zone_keys if discovery else frozenset()
        entities: list[NumberEntity] = []
        for zone_key in zone_keys_from_store(store):
            zone_state = store.zone_state.get(zone_key) or {}
            for spec in zone_number_specs_for_zone(zone_key, zone_state, zone_field_keys):
                entity_key = zone_entity_cache_key(zone_key, spec.suffix)
                if entity_key in added:
                    continue
                entities.append(
                    EureviaRegateZoneSetpointNumber(hass, entry, entry.entry_id, zone_key, spec)
                )
                added.add(entity_key)
        return entities

    setup_dynamic_entities(
        hass,
        entry,
        async_add_entities,
        build_entities,
        (SIGNAL_ZONES_UPDATED, SIGNAL_DISCOVERY_UPDATED),
    )
