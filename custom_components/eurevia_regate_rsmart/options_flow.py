"""Options flow for zone selection and naming."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import selector

from .const import CONF_TELEMETRY, CONF_ZONES
from .lib import slugify_snake


class EureviaRegateOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry
        self._zones_raw: list[dict] = []
        self._selected_ids: list[int] = []
        self._telemetry = bool(config_entry.options.get(CONF_TELEMETRY, False))

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        store = self.hass.data.get(self._entry.domain, {}).get(self._entry.entry_id, {})
        self._zones_raw = store.get("zones_raw") or []
        existing = dict(self._entry.options.get(CONF_ZONES, {}))

        zone_choices: dict[str, str] = {}
        for zone in self._zones_raw:
            zone_id = zone.get("id")
            if zone_id is None:
                continue
            name = zone.get("customName") or zone.get("name") or f"Zone {zone_id}"
            zone_choices[str(int(zone_id))] = str(name)

        if user_input is None:
            default_selected: list[str] = []
            if existing:
                for cfg in existing.values():
                    zid = cfg.get("zone_id")
                    if zid is not None:
                        default_selected.append(str(int(zid)))
            else:
                for zone in self._zones_raw:
                    if zone.get("isClimatic") is True and zone.get("id") is not None:
                        default_selected.append(str(int(zone.get("id"))))

            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            "selected_zone_ids", default=default_selected
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=[
                                    {"value": zone_id, "label": label}
                                    for zone_id, label in zone_choices.items()
                                ],
                                multiple=True,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        ),
                        vol.Required(
                            CONF_TELEMETRY,
                            default=bool(self._entry.options.get(CONF_TELEMETRY, False)),
                        ): selector.BooleanSelector(),
                    }
                ),
            )

        self._selected_ids = [int(item) for item in (user_input.get("selected_zone_ids") or [])]
        self._telemetry = bool(user_input.get(CONF_TELEMETRY, False))
        return await self.async_step_zones()

    async def async_step_zones(self, user_input: dict | None = None) -> ConfigFlowResult:
        store = self.hass.data.get(self._entry.domain, {}).get(self._entry.entry_id, {})
        zones_raw = store.get("zones_raw") or self._zones_raw
        existing = dict(self._entry.options.get(CONF_ZONES, {}))
        selected = [zone for zone in zones_raw if zone.get("id") in self._selected_ids]

        area_reg = ar.async_get(self.hass)
        areas = area_reg.async_list_areas()
        area_choices = {"": self.hass.config.language == "fr" and "(Aucune)" or "(None)"} | {
            area.id: area.name for area in areas
        }

        if user_input is None:
            schema: dict = {}
            for zone in selected:
                zone_id = zone.get("id")
                if zone_id is None:
                    continue
                zone_id = int(zone_id)
                base_name = zone.get("customName") or zone.get("name") or f"Zone {zone_id}"

                prev_key = None
                prev_cfg = None
                for key, cfg in existing.items():
                    if cfg.get("zone_id") == zone_id:
                        prev_key = key
                        prev_cfg = cfg
                        break

                name_default = (prev_cfg or {}).get("name") or base_name
                key_default = (prev_cfg or {}).get("key") or prev_key or slugify_snake(base_name)
                key_default = slugify_snake(key_default)
                area_default = (prev_cfg or {}).get("area_id") or ""

                schema[vol.Required(f"name_{zone_id}", default=name_default)] = str
                schema[vol.Required(f"key_{zone_id}", default=key_default)] = str
                schema[vol.Optional(f"area_{zone_id}", default=area_default)] = vol.In(area_choices)

            return self.async_show_form(step_id="zones", data_schema=vol.Schema(schema))

        new_zones: dict[str, dict] = {}
        for zone in selected:
            zone_id = zone.get("id")
            if zone_id is None:
                continue
            zone_id = int(zone_id)
            base_name = zone.get("customName") or zone.get("name") or f"Zone {zone_id}"

            name = user_input.get(f"name_{zone_id}") or base_name
            key = slugify_snake(user_input.get(f"key_{zone_id}") or name)
            area_id = user_input.get(f"area_{zone_id}") or ""
            if area_id == "":
                area_id = None

            new_zones[key] = {
                "zone_id": zone_id,
                "name": name,
                "key": key,
                "area_id": area_id,
                "devices": list(zone.get("devices") or []),
                "isClimatic": bool(zone.get("isClimatic")),
            }

        return self.async_create_entry(
            title="",
            data={
                CONF_ZONES: new_zones,
                CONF_TELEMETRY: self._telemetry,
            },
        )
