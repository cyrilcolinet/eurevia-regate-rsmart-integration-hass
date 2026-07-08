"""Diagnostics support for Eurevia reGATE."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_PORT, CONF_PREFIX, CONF_TELEMETRY, DOMAIN
from .lib.capabilities import HvacDeviceProfile
from .lib.telemetry_profile import (
    build_github_new_issue_url,
    is_placeholder_thermostat,
    profile_fingerprint,
    profile_needs_telemetry,
    profile_to_export_dict,
    unknown_keys_for_profile,
)
from .store import RegateStore

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
        full_fingerprint = profile_fingerprint(export_dict)
        if not export_dict.get("supported_by_integration") and profile_needs_telemetry(
            profile, unknown_keys
        ):
            export_dict["github_issue_url"] = build_github_new_issue_url(
                export_dict, full_fingerprint
            )
        exports.append(export_dict)
    return sorted(exports, key=lambda item: ",".join(item.get("roles") or []))


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    from . import __version__

    raw_store = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    store: RegateStore | None = raw_store if isinstance(raw_store, RegateStore) else None
    discovery = store.discovery if store else None
    hvac_raw = store.hvac_raw if store else {}
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
    last_message = (
        store.last_mqtt_message_at.isoformat() if store and store.last_mqtt_message_at else None
    )
    return {
        "entry": {
            "title": entry.title,
            CONF_PORT: entry.data.get(CONF_PORT),
            CONF_PREFIX: entry.data.get(CONF_PREFIX),
            "telemetry_enabled": entry.options.get(CONF_TELEMETRY, False),
        },
        "mqtt_connected": store.mqtt_connected if store else None,
        "last_mqtt_message_at": last_message,
        "zones_configured": len(store.zone_cfg) if store else 0,
        "zones_raw_count": len(store.zones_raw) if store else 0,
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
        "zone_mappings": list(store.zone_key_to_hvac_id.items()) if store else [],
        "sample_zone_state": async_redact_data(
            next(iter(store.zone_state.values()), {}),
            REDACT,
        )
        if store and store.zone_state
        else {},
    }
