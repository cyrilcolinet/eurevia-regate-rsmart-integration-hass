"""Fan platform for the auto-discovered reGATE air purifier."""

from __future__ import annotations

import json
from enum import IntEnum
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SIGNAL_DISCOVERY_UPDATED,
    SIGNAL_HVAC_DEVICE_STATE_UPDATED,
    topic_hvac_set,
)
from .entity import EureviaRegateEntity, bloc_cvc_device_info
from .lib import as_int, resolve_purifier_state


class PMode(IntEnum):
    AUTO = 0
    MINI = 1
    MOYEN = 2
    MAXI = 3


PRESET_AUTO = "auto"
PRESET_MINI = "mini"
PRESET_MOYEN = "moyen"
PRESET_MAXI = "maxi"

PRESET_TO_PMODE: dict[str, PMode] = {
    PRESET_AUTO: PMode.AUTO,
    PRESET_MINI: PMode.MINI,
    PRESET_MOYEN: PMode.MOYEN,
    PRESET_MAXI: PMode.MAXI,
}
PMODE_TO_PRESET: dict[int, str] = {int(value): key for key, value in PRESET_TO_PMODE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    added: bool = store.setdefault("added_purifier", False)

    def build_entities() -> list[FanEntity]:
        nonlocal added
        discovery = store.get("discovery")
        if added or not discovery or not discovery.has_purifier:
            return []
        added = True
        return [EureviaRegatePurifierFan(hass, entry, entry.entry_id)]

    async_add_entities(build_entities(), update_before_add=False)

    @callback
    def _discovery_updated() -> None:
        async_add_entities(build_entities(), update_before_add=False)

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{SIGNAL_DISCOVERY_UPDATED}_{entry.entry_id}", _discovery_updated
        )
    )


class EureviaRegatePurifierFan(EureviaRegateEntity, FanEntity):
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
    )
    _attr_percentage_step = 33
    _attr_preset_modes = [PRESET_AUTO, PRESET_MINI, PRESET_MOYEN, PRESET_MAXI]
    _attr_translation_key = "purifier"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str) -> None:
        super().__init__(hass, entry, entry_id)
        self._unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_purifier"

    @property
    def _command_device_id(self) -> str | None:
        discovery = self._store.get("discovery")
        return discovery.purifier_command_id if discovery else None

    def _get_hvac_state(self) -> tuple[dict[str, Any], str | None]:
        return resolve_purifier_state(
            self._store.get("hvac_raw") or {},
            self._store.get("discovery"),
        )

    @property
    def device_info(self):
        return bloc_cvc_device_info(self._entry)

    @property
    def _p_mode(self) -> int | None:
        state, _device_id = self._get_hvac_state()
        if "P_Mode" in state:
            return as_int(state.get("P_Mode"), int(PMode.AUTO))
        return None

    @property
    def is_on(self) -> bool | None:
        return self._p_mode is not None

    @property
    def preset_mode(self) -> str | None:
        mode = self._p_mode
        if mode is None:
            return None
        return PMODE_TO_PRESET.get(int(mode))

    @property
    def percentage(self) -> int | None:
        mode = self._p_mode
        if mode is None:
            return None
        mode = int(mode)
        if mode in (int(PMode.AUTO), int(PMode.MINI)):
            return 33
        if mode == int(PMode.MOYEN):
            return 66
        if mode == int(PMode.MAXI):
            return 100
        return None

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
            return
        if percentage is not None:
            await self.async_set_percentage(percentage)
            return
        await self._publish({"P_Mode": int(PMode.AUTO)})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._publish({"P_Mode": int(PMode.AUTO), "P_Boost": False, "P_Timer": False})

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage <= 33:
            await self._publish({"P_Mode": int(PMode.MINI)})
        elif percentage <= 66:
            await self._publish({"P_Mode": int(PMode.MOYEN)})
        else:
            await self._publish({"P_Mode": int(PMode.MAXI)})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode = PRESET_TO_PMODE.get(preset_mode)
        if mode is None:
            return
        await self._publish({"P_Mode": int(mode)})

    async def _publish(self, payload: dict[str, Any]) -> None:
        device_id = self._command_device_id
        if not device_id:
            return
        topic = topic_hvac_set(self._store["prefix"], device_id)
        await self._store["client"].publish(topic, json.dumps(payload).encode("utf-8"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state, read_device_id = self._get_hvac_state()
        out: dict[str, Any] = {}
        if read_device_id:
            out["read_from_device"] = read_device_id
        if self._command_device_id:
            out["command_device"] = self._command_device_id
        mode = self._p_mode
        if mode is not None:
            out["p_mode"] = int(mode)
            out["preset_mode"] = self.preset_mode
        for key in (
            "P_Timer",
            "P_Timer_Left",
            "P_Timer_Max",
            "P_Timer_Def",
            "P_Fan_S",
            "P_Fan_N",
            "P_Fan_E",
            "P_Boost",
        ):
            if key in state:
                out[key.lower()] = state.get(key)
        return out

    async def async_added_to_hass(self) -> None:
        discovery = self._store.get("discovery")
        device_ids = list(discovery.purifier_read_ids) if discovery else []

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
