"""Anonymized reGATE HVAC profiles for opt-in telemetry and diagnostics."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import quote

from ..const import TELEMETRY_GITHUB_REPO, TELEMETRY_ISSUE_LABELS
from .capabilities import HvacDeviceProfile, HvacRole
from .field_registry import TERMINAL_FIELD_SPECS, ZONE_FIELD_SPECS
from .mapping import PLACEHOLDER_TH_ID, normalize_th_id
from .setpoint_registry import SETPOINT_NUMBER_SPECS

PRIVACY_KEYS = frozenset(
    {
        "Th_ID",
        "Th_Name",
        "Zone_Name",
        "Custom_Zone_Name",
    }
)

EXTRA_KNOWN_ZONE_KEYS = frozenset(
    {
        "Boost",
        "Mode",
        "Mode_Active",
        "Operating_Mode",
        "Override",
        "Tmp",
        "Th_Type",
        "Timer_Def",
        "Window",
        "Detection",
    }
)

EXTRA_KNOWN_TERMINAL_KEYS = frozenset(
    {
        "Actuator_Type",
        "Assembly",
        "Channels",
        "Channels_Bound_Closing",
        "Channels_Bound_Opening",
        "Channels_Cmd",
        "Fan_1C",
        "Fan_2C",
        "Fan_3C",
        "Fan_4C",
        "Fan_5C",
        "Fan_6C",
        "Inverter_Min",
        "Inverter_Min_Summer",
        "MTA",
        "Name",
        "Operating_Mode",
        "P_Boost",
        "P_Fan_E",
        "P_Fan_N",
        "P_Fan_S",
        "P_Mode",
        "P_Timer",
        "P_Timer_Def",
        "P_Timer_Left",
        "P_Timer_Max",
        "Type",
        "Valve_Debugging_Timer",
        "Valve_Heat_Debugging_Timer",
        "Valve_PWM_Timer",
        "Z_Min_Reference_Capacity_Authorize",
        "Z_Step_Speed_2",
        "Z_Step_Speed_3",
        "Z_Step_Speed_4",
        "Z_Temp_Limit_Speed_1",
        "Z_Temp_Limit_Speed_2",
        "Z_brand",
    }
)

# Installer / factory test keys — never surfaced in HA or telemetry.
IGNORED_MQTT_KEY_PREFIXES = ("Test_",)

EXTRA_KNOWN_ACTUATOR_KEYS = frozenset({"Pos_Min", "Pos_Max", "Pos_Cmd"})

EXTRA_KNOWN_SYSTEM_KEYS = frozenset(
    {
        "Comm",
        "Heating_Mode",
        "Mode",
        "Mode_FB",
        "PAC",
    }
)

EXTRA_KNOWN_ZONE_CONFIG_KEYS = frozenset(
    {
        "Channels",
        "Child",
        "DB_Cool",
        "DB_Heat",
        "Detection_Control_Mode",
        "Favorite",
        "ID",
        "Mode_Override",
        "No_Operating_Auth_mode",
        "Stp_Comf_Def",
        "Stp_Comf_Def_Summer",
        "Stp_Comf_Def_Winter",
        "Stp_Comf_Max_Summer",
        "Stp_Comf_Max_Winter",
        "Stp_Comf_Min_Summer",
        "Stp_Comf_Min_Winter",
        "Window_Control_Mode",
    }
)

# Present on every install — tracked on roadmap, not actionable telemetry.
TELEMETRY_SKIP_ROLES = HvacRole.SYSTEM | HvacRole.SCHEDULER

UNIMPLEMENTED_ROLES = HvacRole.ACTUATOR | HvacRole.SYSTEM | HvacRole.SCHEDULER
IMPLEMENTED_ROLES = HvacRole.THERMOSTAT | HvacRole.TERMINAL | HvacRole.PURIFIER

_ROLE_LABELS: tuple[tuple[str, HvacRole], ...] = (
    ("thermostat", HvacRole.THERMOSTAT),
    ("terminal", HvacRole.TERMINAL),
    ("purifier", HvacRole.PURIFIER),
    ("actuator", HvacRole.ACTUATOR),
    ("system", HvacRole.SYSTEM),
    ("scheduler", HvacRole.SCHEDULER),
)

_TELEMETRY_REASON_LABELS = {
    "unknown_mqtt_keys": "MQTT payload contains keys not mapped by the integration yet",
    "unimplemented_role": "Device role detected but not exposed in Home Assistant yet",
    "unsupported_profile": "No Home Assistant entities are created for this profile yet",
}

_GITHUB_ISSUE_URL_MAX_LENGTH = 7500


def known_mqtt_keys() -> frozenset[str]:
    keys: set[str] = set()
    keys.update(spec.mqtt_key for spec in TERMINAL_FIELD_SPECS)
    keys.update(spec.mqtt_key for spec in ZONE_FIELD_SPECS)
    keys.update(spec.mqtt_key for spec in SETPOINT_NUMBER_SPECS)
    keys.update(EXTRA_KNOWN_ZONE_KEYS)
    keys.update(EXTRA_KNOWN_TERMINAL_KEYS)
    keys.update(EXTRA_KNOWN_ACTUATOR_KEYS)
    keys.update(EXTRA_KNOWN_SYSTEM_KEYS)
    keys.update(EXTRA_KNOWN_ZONE_CONFIG_KEYS)
    return frozenset(keys)


def roles_to_strings(roles: HvacRole) -> list[str]:
    return [label for label, flag in _ROLE_LABELS if roles & flag]


def ha_platforms_for_roles(roles: HvacRole) -> list[str]:
    platforms: set[str] = set()
    if roles & HvacRole.THERMOSTAT:
        platforms.update({"climate", "sensor", "number", "binary_sensor"})
    if roles & HvacRole.TERMINAL:
        platforms.add("sensor")
    if roles & HvacRole.PURIFIER:
        platforms.update({"fan", "sensor"})
    if roles & HvacRole.ACTUATOR:
        platforms.add("cover")
    if roles & HvacRole.SYSTEM:
        platforms.add("select")
    if roles & HvacRole.SCHEDULER:
        platforms.add("schedule")
    return sorted(platforms)


def unknown_keys_for_profile(profile: HvacDeviceProfile) -> list[str]:
    known = known_mqtt_keys()
    return sorted(
        key
        for key in profile.keys
        if key not in known
        and key not in PRIVACY_KEYS
        and not any(key.startswith(prefix) for prefix in IGNORED_MQTT_KEY_PREFIXES)
    )


def is_placeholder_thermostat(
    profile: HvacDeviceProfile,
    hvac_raw: dict[str, dict[str, Any]],
) -> bool:
    payload = hvac_raw.get(profile.device_id) or {}
    if not isinstance(payload, dict):
        return False
    th_id = normalize_th_id(payload.get("Th_ID"))
    return th_id == PLACEHOLDER_TH_ID


def unimplemented_roles_for_telemetry(roles: HvacRole) -> list[str]:
    flags = roles & UNIMPLEMENTED_ROLES
    if roles & HvacRole.THERMOSTAT:
        flags &= ~HvacRole.ACTUATOR
    if roles & (HvacRole.TERMINAL | HvacRole.PURIFIER):
        flags &= ~HvacRole.PURIFIER
    return roles_to_strings(flags)


def profile_supported_by_integration(
    profile: HvacDeviceProfile,
    unknown_keys: list[str],
) -> bool:
    if profile.roles == HvacRole.NONE:
        return False
    if unknown_keys:
        return False
    if not (profile.roles & IMPLEMENTED_ROLES):
        return False
    return not unimplemented_roles_for_telemetry(profile.roles)


def profile_needs_telemetry(
    profile: HvacDeviceProfile,
    unknown_keys: list[str],
) -> bool:
    if profile.roles == HvacRole.NONE:
        return False
    if profile.roles & TELEMETRY_SKIP_ROLES and not (profile.roles & ~TELEMETRY_SKIP_ROLES):
        return False
    if unknown_keys:
        return True
    if unimplemented_roles_for_telemetry(profile.roles):
        return True
    return bool(not (profile.roles & IMPLEMENTED_ROLES))


def telemetry_reason(
    profile: HvacDeviceProfile,
    unknown_keys: list[str],
) -> str | None:
    if not profile_needs_telemetry(profile, unknown_keys):
        return None
    if unknown_keys:
        return "unknown_mqtt_keys"
    if unimplemented_roles_for_telemetry(profile.roles):
        return "unimplemented_role"
    return "unsupported_profile"


def profile_to_export_dict(
    profile: HvacDeviceProfile,
    *,
    unknown_keys: list[str],
    integration_version: str,
    ha_version: str,
) -> dict[str, Any]:
    roles = roles_to_strings(profile.roles)
    supported = profile_supported_by_integration(profile, unknown_keys)
    export: dict[str, Any] = {
        "roles": roles,
        "mqtt_keys": sorted(key for key in profile.keys if key not in PRIVACY_KEYS),
        "unknown_keys": unknown_keys,
        "supported_by_integration": supported,
        "ha_platforms": ha_platforms_for_roles(profile.roles),
        "integration_version": integration_version,
        "ha_version": ha_version,
    }
    reason = telemetry_reason(profile, unknown_keys)
    if reason:
        export["telemetry_reason"] = reason
    return export


def profile_fingerprint(export_dict: dict[str, Any]) -> str:
    stable = {
        "roles": export_dict.get("roles"),
        "mqtt_keys": sorted(export_dict.get("mqtt_keys") or []),
        "unknown_keys": sorted(export_dict.get("unknown_keys") or []),
    }
    payload = json.dumps(stable, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def format_github_issue_title(export_dict: dict[str, Any]) -> str:
    roles = export_dict.get("roles") or ["unknown"]
    role_label = "+".join(roles[:3])
    if export_dict.get("supported_by_integration"):
        return f"[telemetry] reGATE profile — {role_label}"
    return f"[telemetry] Unsupported reGATE profile — {role_label}"


def format_github_issue_body(export_dict: dict[str, Any], fingerprint: str) -> str:
    supported = "yes" if export_dict.get("supported_by_integration") else "no"
    roles = export_dict.get("roles") or []
    mqtt_keys = export_dict.get("mqtt_keys") or []
    unknown_keys = export_dict.get("unknown_keys") or []

    role_lines = "\n".join(f"- `{role}`" for role in roles) or "- _(none)_"
    key_lines = "\n".join(f"- `{key}`" for key in mqtt_keys) or "- _(none)_"
    unknown_lines = "\n".join(f"- `{key}`" for key in unknown_keys) or "- _(none)_"

    body = (
        "## reGATE device profile (opt-in share)\n\n"
        "Anonymized MQTT key names only — no host, zone names, or thermostat IDs. "
        "Issue opened manually from Home Assistant.\n\n"
        f"- **Roles:** {', '.join(f'`{role}`' for role in roles) or 'unknown'}\n"
        f"- **Supported by integration:** {supported}\n"
        f"- **Integration version:** `{export_dict.get('integration_version', '')}`\n"
        f"- **Home Assistant:** `{export_dict.get('ha_version', '')}`\n"
        f"- **Fingerprint:** `{fingerprint[:16]}`\n"
    )

    if platforms := export_dict.get("ha_platforms"):
        platform_line = ", ".join(f"`{platform}`" for platform in platforms)
        body += f"- **HA platforms (planned or active):** {platform_line}\n"

    if reason := export_dict.get("telemetry_reason"):
        reason_text = _TELEMETRY_REASON_LABELS.get(reason, reason)
        body += f"- **Why this report:** {reason_text}\n"

    body += (
        "\n### Roles\n"
        f"{role_lines}\n\n"
        "### MQTT keys (names only)\n"
        f"{key_lines}\n\n"
        "### Unknown keys\n"
        f"{unknown_lines}\n"
    )
    return body


def build_github_new_issue_url(export_dict: dict[str, Any], fingerprint: str) -> str:
    title = format_github_issue_title(export_dict)
    labels = ",".join(TELEMETRY_ISSUE_LABELS)
    base = f"https://github.com/{TELEMETRY_GITHUB_REPO}/issues/new"
    body = format_github_issue_body(export_dict, fingerprint)
    url = f"{base}?title={quote(title)}&body={quote(body)}&labels={quote(labels)}"
    if len(url) <= _GITHUB_ISSUE_URL_MAX_LENGTH:
        return url
    body = body[:4000] + "\n\n_(body truncated — use HA diagnostics export)_\n"
    return f"{base}?title={quote(title)}&body={quote(body)}&labels={quote(labels)}"
