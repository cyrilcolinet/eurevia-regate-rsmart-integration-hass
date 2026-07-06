"""Binary sensor platform for window and presence per zone."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_ZONE_STATE_UPDATED, SIGNAL_ZONES_UPDATED
from .entity import EureviaRegateEntity, zone_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    added: set[str] = store.setdefault("added_binary_keys", set())

    def zone_keys() -> list[str]:
        return list((store.get("zone_cfg") or {}).keys())

    def build_entities() -> list[BinarySensorEntity]:
        entities: list[BinarySensorEntity] = []
        for zone_key in zone_keys():
            for suffix, entity_cls in (
                ("window", EureviaRegateZoneWindow),
                ("presence", EureviaRegateZonePresence),
            ):
                key = f"{suffix}:{zone_key}"
                if key in added:
                    continue
                entities.append(entity_cls(hass, entry, entry.entry_id, zone_key))
                added.add(key)
        return entities

    async_add_entities(build_entities(), update_before_add=False)

    @callback
    def _zones_updated() -> None:
        async_add_entities(build_entities(), update_before_add=False)

    entry.async_on_unload(
        async_dispatcher_connect(hass, f"{SIGNAL_ZONES_UPDATED}_{entry.entry_id}", _zones_updated)
    )


class _EureviaRegateZoneBinary(EureviaRegateEntity, BinarySensorEntity):
    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str, zone_key: str
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self.zone_key = zone_key
        self._unsub = None

    @property
    def _zone_cfg(self) -> dict:
        return (self._store.get("zone_cfg") or {}).get(self.zone_key, {}) or {}

    @property
    def _zone_state(self) -> dict:
        return (self._store.get("zone_state") or {}).get(self.zone_key, {}) or {}

    @property
    def device_info(self):
        return zone_device_info(self.zone_key, self._zone_cfg)

    async def async_added_to_hass(self) -> None:
        @callback
        def _updated(zone_key: str) -> None:
            if zone_key == self.zone_key:
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


class EureviaRegateZoneWindow(_EureviaRegateZoneBinary):
    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_translation_key = "window"

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str, zone_key: str
    ) -> None:
        super().__init__(hass, entry, entry_id, zone_key)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_window"

    @property
    def is_on(self) -> bool | None:
        value = self._zone_state.get("Window")
        if value is None:
            return None
        return str(value).lower() == "open"


class EureviaRegateZonePresence(_EureviaRegateZoneBinary):
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_translation_key = "presence"

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str, zone_key: str
    ) -> None:
        super().__init__(hass, entry, entry_id, zone_key)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_presence"

    @property
    def is_on(self) -> bool | None:
        value = self._zone_state.get("Detection")
        if value is None:
            return None
        return str(value).lower() == "presence"
