"""Fan platform for the auto-discovered reGATE air purifier."""

from __future__ import annotations

from enum import IntEnum
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_DISCOVERY_UPDATED, SIGNAL_HVAC_DEVICE_STATE_UPDATED
from .entity import EureviaRegateEntity, async_publish_hvac_commands, bloc_cvc_device_info
from .lib import as_int, resolve_purifier_state
from .platform_helpers import setup_dynamic_entities
from .store import get_store


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
    store = get_store(hass, entry.entry_id)

    def build_entities() -> list[FanEntity]:
        if store.purifier_entity_added or not store.discovery.has_purifier:
            return []
        store.purifier_entity_added = True
        return [EureviaRegatePurifierFan(hass, entry, entry.entry_id)]

    setup_dynamic_entities(
        hass,
        entry,
        async_add_entities,
        build_entities,
        (SIGNAL_DISCOVERY_UPDATED,),
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
        self._hvac_unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_purifier"

    @property
    def _command_device_id(self) -> str | None:
        return self._store.discovery.purifier_command_id

    def _get_hvac_state(self) -> tuple[dict[str, Any], str | None]:
        return resolve_purifier_state(self._store.hvac_raw, self._store.discovery)

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
        # reGATE has no true off — AUTO stops boost/timer (see SUPPORTED_DEVICES.md).
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
        discovery = self._store.discovery
        device_ids = list(discovery.purifier_read_ids) if discovery else []
        if not device_ids and self._command_device_id:
            device_ids = [self._command_device_id]
        await async_publish_hvac_commands(self._store, device_ids, payload)

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
        await super().async_added_to_hass()
        discovery = self._store.discovery
        device_ids = list(discovery.purifier_read_ids) if discovery else []

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
