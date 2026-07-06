"""Climate platform for Eurevia reGATE zones and global thermostat."""

from __future__ import annotations

import json
from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, SIGNAL_ZONE_STATE_UPDATED, SIGNAL_ZONES_UPDATED, topic_hvac_set
from .entity import EureviaRegateEntity, bloc_cvc_device_info, zone_device_info
from .lib import as_float, as_int

MODE_OFF = 0
MODE_COMFORT = 1
MODE_ECO = 2
MODE_REDUCED = 3

PRESET_COMFORT = "comfort"
PRESET_ECO = "eco"
PRESET_SLEEP = "sleep"

PRESET_TO_MODE = {
    PRESET_COMFORT: MODE_COMFORT,
    PRESET_ECO: MODE_ECO,
    PRESET_SLEEP: MODE_REDUCED,
}
MODE_TO_PRESET = {
    MODE_COMFORT: PRESET_COMFORT,
    MODE_ECO: PRESET_ECO,
    MODE_REDUCED: PRESET_SLEEP,
}

FAN_AUTO = "auto"
FAN_BOOST = "boost"
GLOBAL_FAN_MODES = [FAN_AUTO, FAN_BOOST]


def _all_equal_strict(values: list[Any]) -> tuple[bool, Any | None]:
    if not values:
        return True, None
    first = values[0]
    for value in values[1:]:
        if value != first:
            return False, None
    return True, first


def _all_equal_ignore_none(values: list[Any]) -> tuple[bool, Any | None]:
    if not values:
        return True, None
    defined = [value for value in values if value is not None]
    if not defined:
        return True, None
    if len(defined) != len(values):
        return False, None
    return _all_equal_strict(defined)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    added_zones: set[str] = store.setdefault("added_climate_zone_keys", set())
    added_global: bool = store.setdefault("added_climate_global", False)

    def zone_keys() -> list[str]:
        return list((store.get("zone_cfg") or {}).keys())

    def build_entities() -> list[ClimateEntity]:
        entities: list[ClimateEntity] = []
        nonlocal added_global
        if not added_global:
            entities.append(EureviaRegateGlobalClimate(hass, entry, entry.entry_id))
            added_global = True
        for zone_key in zone_keys():
            if zone_key in added_zones:
                continue
            entities.append(EureviaRegateZoneClimate(hass, entry, entry.entry_id, zone_key))
            added_zones.add(zone_key)
        return entities

    async_add_entities(build_entities(), update_before_add=False)

    @callback
    def _zones_updated() -> None:
        async_add_entities(build_entities(), update_before_add=False)

    entry.async_on_unload(
        async_dispatcher_connect(hass, f"{SIGNAL_ZONES_UPDATED}_{entry.entry_id}", _zones_updated)
    )


class EureviaRegateZoneClimate(EureviaRegateEntity, ClimateEntity):
    _attr_temperature_unit = "°C"
    _attr_target_temperature_step = 0.5
    _attr_translation_key = "zone"
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_SLEEP]
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str, zone_key: str
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self.zone_key = zone_key
        self._unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_climate"

    @property
    def _zone_cfg(self) -> dict:
        return (self._store.get("zone_cfg") or {}).get(self.zone_key, {})

    @property
    def _state(self) -> dict:
        return (self._store.get("zone_state") or {}).get(self.zone_key, {}) or {}

    @property
    def device_info(self):
        return zone_device_info(self.zone_key, self._zone_cfg)

    @property
    def current_temperature(self) -> float | None:
        return as_float(self._state.get("Tmp"))

    @property
    def target_temperature(self) -> float | None:
        return as_float(self._state.get("Stp_Comf"))

    @property
    def min_temp(self) -> float:
        value = as_float(self._state.get("Stp_Comf_Min"))
        return value if value is not None else super().min_temp

    @property
    def max_temp(self) -> float:
        value = as_float(self._state.get("Stp_Comf_Max"))
        return value if value is not None else super().max_temp

    @property
    def hvac_mode(self) -> HVACMode:
        mode = as_int(self._state.get("Mode"))
        return HVACMode.OFF if mode == MODE_OFF else HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        mode = as_int(self._state.get("Mode"))
        return MODE_TO_PRESET.get(mode) if mode is not None else None

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def _publish(self, payload: dict[str, Any]) -> None:
        hvac_id = (self._store.get("zone_key_to_hvac_id") or {}).get(self.zone_key)
        if not hvac_id:
            return
        topic = topic_hvac_set(self._store["prefix"], hvac_id)
        await self._store["client"].publish(topic, json.dumps(payload).encode("utf-8"))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        payload = {"Mode": MODE_OFF} if hvac_mode == HVACMode.OFF else {"Mode": MODE_COMFORT}
        await self._publish(payload)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode = PRESET_TO_MODE.get(preset_mode)
        if mode is None:
            return
        await self._publish({"Mode": mode})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        try:
            temp_value = float(temp)
        except (TypeError, ValueError):
            return
        await self._publish({"Mode": MODE_COMFORT, "Stp_Comf": temp_value})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            key.lower(): self._state[key]
            for key in (
                "Zone_Name",
                "Th_Name",
                "Th_ID",
                "Operating_Mode",
                "Mode_Active",
                "Override",
                "Authorized",
                "Battery",
                "Window",
                "Detection",
                "Water_Auth",
                "Operating_Auth",
                "Com_Th",
                "RH",
                "Tmp_Offset",
                "Boost",
            )
            if key in self._state
        }

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


class EureviaRegateGlobalClimate(EureviaRegateEntity, ClimateEntity):
    _attr_temperature_unit = "°C"
    _attr_target_temperature_step = 0.5
    _attr_translation_key = "global"
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.FAN_MODE
    )
    _attr_preset_modes = [PRESET_COMFORT, PRESET_ECO, PRESET_SLEEP]
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_fan_modes = GLOBAL_FAN_MODES

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str) -> None:
        super().__init__(hass, entry, entry_id)
        self._unsub = None
        self._debounce_unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_global_climate"

    def _zone_hvac_ids(self) -> list[str]:
        mapping = self._store.get("zone_key_to_hvac_id") or {}
        return [str(value) for _, value in sorted(mapping.items()) if value]

    def _zone_states(self) -> list[dict]:
        zone_state = self._store.get("zone_state") or {}
        return [zone_state.get(zone_key) or {} for zone_key in (self._store.get("zone_cfg") or {})]

    @property
    def device_info(self):
        return bloc_cvc_device_info(self._entry)

    @property
    def hvac_mode(self) -> HVACMode:
        modes = [as_int(state.get("Mode")) for state in self._zone_states()]
        defined = [mode for mode in modes if mode is not None]
        if defined and all(mode == MODE_OFF for mode in defined):
            return HVACMode.OFF
        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        modes = [as_int(state.get("Mode")) for state in self._zone_states()]
        equal, common = _all_equal_ignore_none(modes)
        if not equal or common is None:
            return None
        return MODE_TO_PRESET.get(common)

    @property
    def target_temperature(self) -> float | None:
        temps = [as_float(state.get("Stp_Comf")) for state in self._zone_states()]
        equal, common = _all_equal_ignore_none(temps)
        return common if equal else None

    @property
    def current_temperature(self) -> float | None:
        temps = [as_float(state.get("Tmp")) for state in self._zone_states()]
        temps = [temp for temp in temps if temp is not None]
        if not temps:
            return None
        return sum(temps) / len(temps)

    @property
    def fan_mode(self) -> str:
        boosts = [bool(state.get("Boost")) for state in self._zone_states() if "Boost" in state]
        if boosts and all(boosts):
            return FAN_BOOST
        return FAN_AUTO

    async def _publish_all(self, payload: dict[str, Any]) -> None:
        client = self._store["client"]
        prefix = self._store["prefix"]
        for hvac_id in self._zone_hvac_ids():
            topic = topic_hvac_set(prefix, hvac_id)
            await client.publish(topic, json.dumps(payload).encode("utf-8"))

    async def async_turn_off(self) -> None:
        await self._publish_all({"Mode": MODE_OFF})

    async def async_turn_on(self) -> None:
        await self._publish_all({"Mode": MODE_COMFORT})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode = PRESET_TO_MODE.get(preset_mode)
        if mode is None:
            return
        await self._publish_all({"Mode": mode})

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        try:
            temp_value = float(temp)
        except (TypeError, ValueError):
            return
        await self._publish_all({"Mode": MODE_COMFORT, "Stp_Comf": temp_value})

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        normalized = (fan_mode or "").strip().lower()
        if normalized not in GLOBAL_FAN_MODES:
            return
        await self._publish_all({"Boost": normalized == FAN_BOOST})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        modes = [as_int(state.get("Mode")) for state in self._zone_states()]
        temps = [as_float(state.get("Stp_Comf")) for state in self._zone_states()]
        boosts_raw = [state.get("Boost") for state in self._zone_states() if "Boost" in state]
        return {
            "mixed_modes": not _all_equal_ignore_none(modes)[0],
            "mixed_setpoint": not _all_equal_ignore_none(temps)[0],
            "mixed_boost": bool(boosts_raw) and not _all_equal_strict(boosts_raw)[0],
            "zone_hvac_ids": self._zone_hvac_ids(),
        }

    async def async_added_to_hass(self) -> None:
        @callback
        def _do_write(_now) -> None:
            self._debounce_unsub = None
            self.async_write_ha_state()

        @callback
        def _updated(_: str) -> None:
            if self._debounce_unsub:
                self._debounce_unsub()
                self._debounce_unsub = None
            self._debounce_unsub = async_call_later(self.hass, 0.2, _do_write)

        self._unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_ZONE_STATE_UPDATED}_{self._entry_id}",
            _updated,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._debounce_unsub:
            self._debounce_unsub()
            self._debounce_unsub = None
        if self._unsub:
            self._unsub()
            self._unsub = None
