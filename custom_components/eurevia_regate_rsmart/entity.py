"""Shared entity behaviour for Eurevia reGATE platforms."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN


class EureviaRegateEntity(Entity):
    """Base class with store access and device helpers."""

    _attr_has_entity_name = True

    def __init__(self, hass, entry: ConfigEntry, entry_id: str) -> None:
        self.hass = hass
        self._entry = entry
        self._entry_id = entry_id

    @property
    def _store(self) -> dict:
        return self.hass.data[DOMAIN][self._entry_id]

    @property
    def entry(self) -> ConfigEntry:
        return self._entry


def bloc_cvc_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Device registry entry for the hydraulic terminal + global climate."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"bloc_cvc_{entry.entry_id}")},
        name="Bloc CVC",
        manufacturer="Eurevia",
        model="reGATE rSMART",
    )


def zone_device_info(zone_key: str, zone_cfg: dict) -> DeviceInfo:
    """Device registry entry for a climatic zone."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"zone_{zone_key}")},
        name=zone_cfg.get("name") or zone_key,
        manufacturer="Eurevia",
        model="reSENS / reGATE Zone",
        suggested_area=zone_cfg.get("area_id"),
    )
