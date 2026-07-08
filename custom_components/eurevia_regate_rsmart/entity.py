"""Shared entity behaviour for Eurevia reGATE platforms."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, SIGNAL_MQTT_CONNECTION_CHANGED, SIGNAL_ZONE_STATE_UPDATED, topic_hvac_set
from .exceptions import MqttNotConnected
from .store import RegateStore, get_store


class EureviaRegateEntity(Entity):
    """Base class with store access, MQTT availability, and device helpers."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str) -> None:
        self.hass = hass
        self._entry = entry
        self._entry_id = entry_id
        self._mqtt_unsub = None

    @property
    def _store(self) -> RegateStore:
        return get_store(self.hass, self._entry_id)

    @property
    def entry(self) -> ConfigEntry:
        return self._entry

    @property
    def available(self) -> bool:
        return super().available and self._store.mqtt_connected

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _mqtt_connection_changed() -> None:
            self.async_write_ha_state()

        self._mqtt_unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_MQTT_CONNECTION_CHANGED}_{self._entry_id}",
            _mqtt_connection_changed,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._mqtt_unsub:
            self._mqtt_unsub()
            self._mqtt_unsub = None
        await super().async_will_remove_from_hass()


class EureviaZoneEntity(EureviaRegateEntity):
    """Zone-scoped entity with cfg/state accessors and zone update subscription."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str, zone_key: str
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self._zone_key = zone_key
        self._zone_unsub = None

    @property
    def zone_key(self) -> str:
        return self._zone_key

    @property
    def _zone_cfg(self) -> dict[str, Any]:
        return self._store.zone_cfg.get(self._zone_key, {}) or {}

    @property
    def _zone_state(self) -> dict[str, Any]:
        return self._store.zone_state.get(self._zone_key, {}) or {}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _updated(zone_key: str) -> None:
            if zone_key == self._zone_key:
                self.async_write_ha_state()

        self._zone_unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_ZONE_STATE_UPDATED}_{self._entry_id}",
            _updated,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._zone_unsub:
            self._zone_unsub()
            self._zone_unsub = None
        await super().async_will_remove_from_hass()


async def async_publish_hvac_command(
    store: RegateStore,
    device_id: str,
    payload: dict[str, Any],
) -> None:
    if not device_id:
        raise MqttNotConnected("mqtt_no_device")
    client = store.client
    if client is None or not store.mqtt_connected:
        raise MqttNotConnected()
    topic = topic_hvac_set(store.prefix, device_id)
    try:
        await client.publish(topic, json.dumps(payload).encode("utf-8"))
    except RuntimeError as err:
        raise MqttNotConnected() from err


async def async_publish_hvac_commands(
    store: RegateStore,
    device_ids: list[str],
    payload: dict[str, Any],
) -> None:
    if not device_ids:
        raise MqttNotConnected("mqtt_no_device")
    encoded = json.dumps(payload).encode("utf-8")
    client = store.client
    if client is None or not store.mqtt_connected:
        raise MqttNotConnected()
    for device_id in device_ids:
        topic = topic_hvac_set(store.prefix, device_id)
        try:
            await client.publish(topic, encoded)
        except RuntimeError as err:
            raise MqttNotConnected() from err


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
