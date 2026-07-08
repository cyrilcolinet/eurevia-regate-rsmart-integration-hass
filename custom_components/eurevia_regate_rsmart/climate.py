"""Climate platform for Eurevia reGATE zones and global thermostat."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, SIGNAL_ZONE_STATE_UPDATED, SIGNAL_ZONES_UPDATED
from .entity import (
    EureviaRegateEntity,
    EureviaZoneEntity,
    async_publish_hvac_command,
    async_publish_hvac_commands,
    bloc_cvc_device_info,
    zone_device_info,
)
from .lib import as_float, as_int
from .lib.hvac_mode import aggregate_zone_hvac_action
from .lib.setpoints import (
    MODE_COMFORT,
    MODE_ECO,
    MODE_OFF,
    MODE_REDUCED,
    read_active_setpoint,
    resolve_zone_hvac_action,
    write_setpoint_payload,
    zone_supports_cooling,
)
from .lib.system_control import async_apply_system_cooling
from .platform_helpers import setup_dynamic_entities, zone_keys_from_store
from .store import get_store

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

HVAC_ACTION_TO_MODE = {
    "off": HVACMode.OFF,
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
    "heat_cool": HVACMode.HEAT_COOL,
}


def _zone_hvac_modes(state: dict, discovery) -> list[HVACMode]:
    modes = [HVACMode.OFF, HVACMode.HEAT]
    zone_keys = discovery.zone_keys if discovery else frozenset()
    if zone_supports_cooling(state, zone_keys) or (discovery and discovery.system_id):
        modes.append(HVACMode.COOL)
    return modes


def _global_hvac_modes(store) -> list[HVACMode]:
    discovery = store.discovery
    modes = [HVACMode.OFF, HVACMode.HEAT]
    zone_keys = discovery.zone_keys if discovery else frozenset()
    supports_cooling = bool(discovery and discovery.system_id)
    if not supports_cooling:
        for zone_key in store.zone_cfg:
            state = store.zone_state.get(zone_key) or {}
            if zone_supports_cooling(state, zone_keys):
                supports_cooling = True
                break
    if supports_cooling:
        modes.extend([HVACMode.COOL, HVACMode.HEAT_COOL])
    return modes


def _action_from_hvac_mode(hvac_mode: HVACMode) -> str:
    if hvac_mode == HVACMode.OFF:
        return "off"
    if hvac_mode == HVACMode.COOL:
        return "cool"
    if hvac_mode == HVACMode.HEAT_COOL:
        return "heat_cool"
    return "heat"


async def _apply_zone_hvac_action(
    store,
    publish,
    *,
    state: dict,
    action: str,
) -> None:
    if action == "off":
        await async_apply_system_cooling(store, cooling=False)
        await publish({"Mode": MODE_OFF})
        return
    if action == "cool":
        await async_apply_system_cooling(store, cooling=True)
    else:
        await async_apply_system_cooling(store, cooling=False)
    mode = as_int(state.get("Mode"))
    if mode == MODE_OFF or mode is None:
        await publish({"Mode": MODE_COMFORT})


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
    store = get_store(hass, entry.entry_id)
    added_zones = store.added("climate_zone")

    def build_entities() -> list[ClimateEntity]:
        entities: list[ClimateEntity] = []
        if not store.climate_global_added:
            entities.append(EureviaRegateGlobalClimate(hass, entry, entry.entry_id))
            store.climate_global_added = True
        for zone_key in zone_keys_from_store(store):
            if zone_key in added_zones:
                continue
            entities.append(EureviaRegateZoneClimate(hass, entry, entry.entry_id, zone_key))
            added_zones.add(zone_key)
        return entities

    setup_dynamic_entities(
        hass,
        entry,
        async_add_entities,
        build_entities,
        (SIGNAL_ZONES_UPDATED,),
    )


class EureviaRegateZoneClimate(EureviaZoneEntity, ClimateEntity):
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

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str, zone_key: str
    ) -> None:
        super().__init__(hass, entry, entry_id, zone_key)
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_zone_{zone_key}_climate"

    @property
    def device_info(self):
        return zone_device_info(self._zone_key, self._zone_cfg)

    @property
    def current_temperature(self) -> float | None:
        return as_float(self._zone_state.get("Tmp"))

    @property
    def target_temperature(self) -> float | None:
        return read_active_setpoint(self._zone_state)

    @property
    def min_temp(self) -> float:
        value = as_float(self._zone_state.get("Stp_Comf_Min"))
        return value if value is not None else super().min_temp

    @property
    def max_temp(self) -> float:
        value = as_float(self._zone_state.get("Stp_Comf_Max"))
        return value if value is not None else super().max_temp

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return _zone_hvac_modes(self._zone_state, self._store.discovery)

    @property
    def hvac_mode(self) -> HVACMode:
        return HVAC_ACTION_TO_MODE[resolve_zone_hvac_action(self._zone_state)]

    @property
    def preset_mode(self) -> str | None:
        mode = as_int(self._zone_state.get("Mode"))
        return MODE_TO_PRESET.get(mode) if mode is not None else None

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def _publish(self, payload: dict[str, Any]) -> None:
        hvac_id = self._store.zone_key_to_hvac_id.get(self._zone_key)
        await async_publish_hvac_command(
            self._store,
            str(hvac_id) if hvac_id else "",
            payload,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await _apply_zone_hvac_action(
            self._store,
            self._publish,
            state=self._zone_state,
            action=_action_from_hvac_mode(hvac_mode),
        )

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
        await self._publish(write_setpoint_payload(self._zone_state, temp_value))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            key.lower(): self._zone_state[key]
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
            if key in self._zone_state
        }


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
    _attr_fan_modes = GLOBAL_FAN_MODES

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_id: str) -> None:
        super().__init__(hass, entry, entry_id)
        self._zone_unsub = None
        self._debounce_unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_global_climate"

    def _zone_hvac_ids(self) -> list[str]:
        return [str(value) for _, value in sorted(self._store.zone_key_to_hvac_id.items()) if value]

    def _zone_states(self) -> list[dict]:
        return [self._store.zone_state.get(zone_key) or {} for zone_key in self._store.zone_cfg]

    @property
    def device_info(self):
        return bloc_cvc_device_info(self._entry)

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return _global_hvac_modes(self._store)

    @property
    def hvac_mode(self) -> HVACMode:
        return HVAC_ACTION_TO_MODE[aggregate_zone_hvac_action(self._zone_states())]

    @property
    def preset_mode(self) -> str | None:
        modes = [as_int(state.get("Mode")) for state in self._zone_states()]
        equal, common = _all_equal_ignore_none(modes)
        if not equal or common is None:
            return None
        return MODE_TO_PRESET.get(common)

    @property
    def target_temperature(self) -> float | None:
        temps = [read_active_setpoint(state) for state in self._zone_states()]
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
        await async_publish_hvac_commands(self._store, self._zone_hvac_ids(), payload)

    async def async_turn_off(self) -> None:
        await self._publish_all({"Mode": MODE_OFF})
        await async_apply_system_cooling(self._store, cooling=False)

    async def async_turn_on(self) -> None:
        await async_apply_system_cooling(self._store, cooling=False)
        await self._publish_all({"Mode": MODE_COMFORT})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        action = _action_from_hvac_mode(hvac_mode)
        if action == "off":
            await self._publish_all({"Mode": MODE_OFF})
            await async_apply_system_cooling(self._store, cooling=False)
            return
        if action == "cool":
            await async_apply_system_cooling(self._store, cooling=True)
        elif action == "heat":
            await async_apply_system_cooling(self._store, cooling=False)
        if action in ("heat", "cool", "heat_cool"):
            payload = {"Mode": MODE_COMFORT}
            for zone_key, hvac_id in sorted(self._store.zone_key_to_hvac_id.items()):
                if not hvac_id:
                    continue
                state = self._store.zone_state.get(zone_key) or {}
                mode = as_int(state.get("Mode"))
                if mode == MODE_OFF or mode is None:
                    await async_publish_hvac_command(self._store, str(hvac_id), payload)

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
        for zone_key, hvac_id in sorted(self._store.zone_key_to_hvac_id.items()):
            if not hvac_id:
                continue
            state = self._store.zone_state.get(zone_key) or {}
            await async_publish_hvac_command(
                self._store,
                str(hvac_id),
                write_setpoint_payload(state, temp_value),
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        normalized = (fan_mode or "").strip().lower()
        if normalized not in GLOBAL_FAN_MODES:
            return
        await self._publish_all({"Boost": normalized == FAN_BOOST})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        modes = [as_int(state.get("Mode")) for state in self._zone_states()]
        temps = [read_active_setpoint(state) for state in self._zone_states()]
        boosts_raw = [state.get("Boost") for state in self._zone_states() if "Boost" in state]
        return {
            "mixed_modes": not _all_equal_ignore_none(modes)[0],
            "mixed_setpoint": not _all_equal_ignore_none(temps)[0],
            "mixed_boost": bool(boosts_raw) and not _all_equal_strict(boosts_raw)[0],
            "zone_hvac_ids": self._zone_hvac_ids(),
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

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

        self._zone_unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_ZONE_STATE_UPDATED}_{self._entry_id}",
            _updated,
        )

    async def async_will_remove_from_hass(self) -> None:
        if self._debounce_unsub:
            self._debounce_unsub()
            self._debounce_unsub = None
        if self._zone_unsub:
            self._zone_unsub()
            self._zone_unsub = None
        await super().async_will_remove_from_hass()
