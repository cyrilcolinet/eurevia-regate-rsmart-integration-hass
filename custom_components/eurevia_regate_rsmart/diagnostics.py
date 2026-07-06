"""Diagnostics support for Eurevia reGATE."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, CONF_PREFIX, DOMAIN

REDACT = {CONF_HOST, "Th_ID", "Th_Name", "Zone_Name", "Custom_Zone_Name"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    discovery = store.get("discovery")
    return {
        "entry": {
            "title": entry.title,
            CONF_PORT: entry.data.get(CONF_PORT),
            CONF_PREFIX: entry.data.get(CONF_PREFIX),
        },
        "zones_configured": len(store.get("zone_cfg") or {}),
        "zones_raw_count": len(store.get("zones_raw") or []),
        "hvac_devices_count": len(store.get("hvac_raw") or {}),
        "discovery": {
            "terminal_primary_id": discovery.terminal_primary_id if discovery else None,
            "terminal_read_ids": list(discovery.terminal_read_ids) if discovery else [],
            "purifier_command_id": discovery.purifier_command_id if discovery else None,
            "purifier_read_ids": list(discovery.purifier_read_ids) if discovery else [],
            "system_id": discovery.system_id if discovery else None,
            "thermostat_ids": list(discovery.thermostat_ids) if discovery else [],
            "actuator_ids": list(discovery.actuator_ids) if discovery else [],
            "scheduler_id": discovery.scheduler_id if discovery else None,
            "terminal_keys_count": len(discovery.terminal_keys) if discovery else 0,
            "zone_keys_count": len(discovery.zone_keys) if discovery else 0,
        },
        "zone_mappings": list((store.get("zone_key_to_hvac_id") or {}).items()),
        "sample_zone_state": async_redact_data(
            next(iter((store.get("zone_state") or {}).values()), {}),
            REDACT,
        ),
    }
