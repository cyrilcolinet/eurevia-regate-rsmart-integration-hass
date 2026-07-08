"""Number platform for writable zone setpoints discovered from MQTT."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SIGNAL_DISCOVERY_UPDATED,
    SIGNAL_HVAC_DEVICE_STATE_UPDATED,
    SIGNAL_ZONES_UPDATED,
)
from .entity import (
    EureviaRegateEntity,
    EureviaZoneEntity,
    async_publish_hvac_command,
    regate_scheduler_device_info,
    regate_system_device_info,
    zone_device_info,
)
from .lib import as_float
from .lib.entity_discovery import zone_entity_cache_key, zone_number_specs_for_zone
from .lib.scheduler_registry import SchedulerNumberSpec, scheduler_number_specs_for_keys
from .lib.setpoint_registry import SetpointNumberSpec
from .lib.system_registry import SystemNumberSpec, system_number_specs_for_keys
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


class EureviaRegateSystemNumber(EureviaRegateEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        spec: SystemNumberSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self._spec = spec
        self._hvac_unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_system_{spec.suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_native_step = spec.step

    @property
    def device_info(self):
        return regate_system_device_info(self._entry)

    @property
    def _system_state(self) -> dict:
        discovery = self._store.discovery
        if not discovery or not discovery.system_id:
            return {}
        payload = self._store.hvac_raw.get(discovery.system_id)
        return payload if isinstance(payload, dict) else {}

    @property
    def native_value(self) -> float | None:
        return as_float(self._system_state.get(self._spec.mqtt_key))

    @property
    def native_min_value(self) -> float:
        return self._spec.min_value

    @property
    def native_max_value(self) -> float:
        return self._spec.max_value

    async def async_set_native_value(self, value: float) -> None:
        discovery = self._store.discovery
        if not discovery or not discovery.system_id:
            raise ValueError("system device unavailable")
        await async_publish_hvac_command(
            self._store,
            discovery.system_id,
            {self._spec.mqtt_key: int(value) if value.is_integer() else float(value)},
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _updated(device_id: str) -> None:
            discovery = self._store.discovery
            if discovery and discovery.system_id == device_id:
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


class EureviaRegateSchedulerNumber(EureviaRegateEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        entry_id: str,
        spec: SchedulerNumberSpec,
    ) -> None:
        super().__init__(hass, entry, entry_id)
        self._spec = spec
        self._hvac_unsub = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_scheduler_{spec.suffix}"
        self._attr_translation_key = spec.translation_key
        self._attr_native_step = spec.step
        if spec.unit is not None:
            self._attr_native_unit_of_measurement = spec.unit

    @property
    def device_info(self):
        return regate_scheduler_device_info(self._entry)

    @property
    def _scheduler_state(self) -> dict:
        discovery = self._store.discovery
        if not discovery or not discovery.scheduler_id:
            return {}
        payload = self._store.hvac_raw.get(discovery.scheduler_id)
        return payload if isinstance(payload, dict) else {}

    @property
    def native_value(self) -> float | None:
        return as_float(self._scheduler_state.get(self._spec.mqtt_key))

    @property
    def native_min_value(self) -> float:
        return self._spec.min_value

    @property
    def native_max_value(self) -> float:
        return self._spec.max_value

    async def async_set_native_value(self, value: float) -> None:
        discovery = self._store.discovery
        if not discovery or not discovery.scheduler_id:
            raise ValueError("scheduler device unavailable")
        await async_publish_hvac_command(
            self._store,
            discovery.scheduler_id,
            {self._spec.mqtt_key: int(value) if value.is_integer() else float(value)},
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _updated(device_id: str) -> None:
            discovery = self._store.discovery
            if discovery and discovery.scheduler_id == device_id:
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
        if discovery and discovery.system_id:
            system_state = store.hvac_raw.get(discovery.system_id) or {}
            if isinstance(system_state, dict):
                for spec in system_number_specs_for_keys(frozenset(system_state.keys())):
                    entity_key = f"system:{spec.suffix}"
                    if entity_key in added:
                        continue
                    entities.append(EureviaRegateSystemNumber(hass, entry, entry.entry_id, spec))
                    added.add(entity_key)
        if discovery and discovery.scheduler_id:
            scheduler_state = store.hvac_raw.get(discovery.scheduler_id) or {}
            if isinstance(scheduler_state, dict):
                for spec in scheduler_number_specs_for_keys(frozenset(scheduler_state.keys())):
                    entity_key = f"scheduler:{spec.suffix}"
                    if entity_key in added:
                        continue
                    entities.append(EureviaRegateSchedulerNumber(hass, entry, entry.entry_id, spec))
                    added.add(entity_key)
        return entities

    setup_dynamic_entities(
        hass,
        entry,
        async_add_entities,
        build_entities,
        (SIGNAL_ZONES_UPDATED, SIGNAL_DISCOVERY_UPDATED, SIGNAL_HVAC_DEVICE_STATE_UPDATED),
    )
