"""Diagnostics support for Eurevia reGATE."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, CONF_PREFIX, CONF_TELEMETRY, DOMAIN
from .lib.capabilities import HvacDeviceProfile
from .lib.telemetry_profile import (
    is_placeholder_thermostat,
    profile_fingerprint,
    profile_to_export_dict,
    unknown_keys_for_profile,
)

REDACT = {CONF_HOST, "Th_ID", "Th_Name", "Zone_Name", "Custom_Zone_Name"}


def _profile_exports(
    profiles: dict[str, HvacDeviceProfile],
    hvac_raw: dict[str, dict[str, Any]],
    *,
    integration_version: str,
    ha_version: str,
) -> list[dict[str, Any]]:
    exports: list[dict[str, Any]] = []
    for profile in profiles.values():
        if is_placeholder_thermostat(profile, hvac_raw):
            continue
        unknown_keys = unknown_keys_for_profile(profile)
        export_dict = profile_to_export_dict(
            profile,
            unknown_keys=unknown_keys,
            integration_version=integration_version,
            ha_version=ha_version,
        )
        export_dict["fingerprint"] = profile_fingerprint(export_dict)[:16]
        exports.append(export_dict)
    return sorted(exports, key=lambda item: ",".join(item.get("roles") or []))


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    from . import __version__

    store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    discovery = store.get("discovery")
    hvac_raw = store.get("hvac_raw") or {}
    ha_version = str(getattr(hass.config, "version", "unknown"))
    profiles = (
        _profile_exports(
            discovery.profiles,
            hvac_raw,
            integration_version=__version__,
            ha_version=ha_version,
        )
        if discovery
        else []
    )
    return {
        "entry": {
            "title": entry.title,
            CONF_PORT: entry.data.get(CONF_PORT),
            CONF_PREFIX: entry.data.get(CONF_PREFIX),
            "telemetry_enabled": entry.options.get(CONF_TELEMETRY, False),
        },
        "zones_configured": len(store.get("zone_cfg") or {}),
        "zones_raw_count": len(store.get("zones_raw") or []),
        "hvac_devices_count": len(hvac_raw),
        "discovery": {
            "terminal_primary_id": discovery.terminal_primary_id if discovery else None,
            "terminal_read_ids": list(discovery.terminal_read_ids) if discovery else [],
            "purifier_command_id": discovery.purifier_command_id if discovery else None,
            "purifier_read_ids": list(discovery.purifier_read_ids) if discovery else [],
            "system_id": discovery.system_id if discovery else None,
            "thermostat_ids": list(discovery.thermostat_ids) if discovery else [],
            "actuator_ids": list(discovery.actuator_ids) if discovery else [],
            "scheduler_id": discovery.scheduler_id if discovery else None,
            "terminal_keys": sorted(discovery.terminal_keys) if discovery else [],
            "zone_keys": sorted(discovery.zone_keys) if discovery else [],
        },
        "hvac_profiles": profiles,
        "zone_mappings": list((store.get("zone_key_to_hvac_id") or {}).items()),
        "sample_zone_state": async_redact_data(
            next(iter((store.get("zone_state") or {}).values()), {}),
            REDACT,
        ),
    }
