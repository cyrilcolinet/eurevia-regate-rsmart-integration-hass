"""Binary sensor platform for window and presence per zone."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY_UPDATED, SIGNAL_ZONES_UPDATED
from .entity import EureviaZoneEntity, zone_device_info
from .lib.binary_registry import ZONE_BINARY_SPECS, BinarySensorSpec
from .lib.entity_discovery import zone_entity_cache_key
from .platform_helpers import setup_dynamic_entities, zone_keys_from_store
from .store import get_store


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = get_store(hass, entry.entry_id)
    added = store.added("binary")

    def build_entities() -> list[BinarySensorEntity]:
        entities: list[BinarySensorEntity] = []
        for zone_key in zone_keys_from_store(store):
            zone_state = store.zone_state.get(zone_key) or {}
            for spec in ZONE_BINARY_SPECS:
                if spec.mqtt_key not in zone_state:
                    continue
                entity_key = zone_entity_cache_key(zone_key, spec.suffix)
                if entity_key in added:
                    continue
                entities.append(_ZoneBinarySensor(hass, entry, entry.entry_id, zone_key, spec))
                added.add(entity_key)
        return entities

    setup_dynamic_entities(
        hass,
        entry,
        async_add_entities,
        build_entities,
        (SIGNAL_ZONES_UPDATED, SIGNAL_DISCOVERY_UPDATED),
    )


class _ZoneBinarySensor(EureviaZoneEntity, BinarySensorEntity):
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        zone_key: str,
        spec: BinarySensorSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id, zone_key)
        self._spec = spec
        self._attr_device_class = spec.device_class
        self._attr_translation_key = spec.translation_key
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_{spec.suffix}"

    @property
    def device_info(self):
        return zone_device_info(self._zone_key, self._zone_cfg)

    @property
    def is_on(self) -> bool | None:
        return self._spec.is_on_fn(self._zone_state.get(self._spec.mqtt_key))
