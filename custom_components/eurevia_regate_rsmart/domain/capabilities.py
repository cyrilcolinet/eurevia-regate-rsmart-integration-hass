"""HVAC device role detection from reGATE MQTT payload patterns."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Flag, auto
from typing import Any

from .mapping import is_thermostat_hvac_payload

TERMINAL_SIGNATURE_KEYS = frozenset(
    {"Water_Temp", "Air_Temp", "Valve_Cmd", "Valve_Cmd_Corrected", "Assembly", "Fan_Speed"}
)
PURIFIER_SIGNATURE_KEYS = frozenset({"P_Mode"})
ACTUATOR_SIGNATURE_KEYS = frozenset({"Pos_Min", "Window"})
SYSTEM_SIGNATURE_KEYS = frozenset({"Heating_Mode", "PAC"})
SCHEDULER_SIGNATURE_KEYS = frozenset({"Day", "Night", "Stp"})


class HvacRole(Flag):
    NONE = 0
    THERMOSTAT = auto()
    TERMINAL = auto()
    PURIFIER = auto()
    ACTUATOR = auto()
    SYSTEM = auto()
    SCHEDULER = auto()


@dataclass(frozen=True, slots=True)
class HvacDeviceProfile:
    device_id: str
    roles: HvacRole
    keys: frozenset[str]


@dataclass(frozen=True, slots=True)
class HvacDiscovery:
    profiles: dict[str, HvacDeviceProfile]
    terminal_primary_id: str | None
    terminal_read_ids: tuple[str, ...]
    purifier_command_id: str | None
    purifier_read_ids: tuple[str, ...]
    system_id: str | None
    thermostat_ids: tuple[str, ...]
    actuator_ids: tuple[str, ...]
    scheduler_id: str | None
    terminal_keys: frozenset[str]
    zone_keys: frozenset[str]

    @property
    def has_purifier(self) -> bool:
        return self.purifier_command_id is not None

    @property
    def has_terminal(self) -> bool:
        return self.terminal_primary_id is not None


def _device_sort_key(device_id: str) -> tuple[int, str]:
    try:
        return (0, f"{int(device_id):010d}")
    except ValueError:
        return (1, device_id)


def classify_hvac_payload(device_id: str, payload: dict[str, Any]) -> HvacDeviceProfile:
    keys = frozenset(payload.keys())
    roles = HvacRole.NONE

    if is_thermostat_hvac_payload(payload):
        roles |= HvacRole.THERMOSTAT
    if keys & TERMINAL_SIGNATURE_KEYS:
        roles |= HvacRole.TERMINAL
    if keys & PURIFIER_SIGNATURE_KEYS:
        roles |= HvacRole.PURIFIER
    if keys & ACTUATOR_SIGNATURE_KEYS:
        roles |= HvacRole.ACTUATOR
    if keys & SYSTEM_SIGNATURE_KEYS:
        roles |= HvacRole.SYSTEM
    if keys & SCHEDULER_SIGNATURE_KEYS and not (roles & HvacRole.THERMOSTAT):
        roles |= HvacRole.SCHEDULER

    return HvacDeviceProfile(device_id=device_id, roles=roles, keys=keys)


def discover_hvac_devices(
    hvac_raw: dict[str, dict[str, Any]],
    zone_state: dict[str, dict[str, Any]] | None = None,
) -> HvacDiscovery:
    profiles: dict[str, HvacDeviceProfile] = {}
    for device_id, payload in hvac_raw.items():
        if isinstance(payload, dict):
            profiles[str(device_id)] = classify_hvac_payload(str(device_id), payload)

    def ids_with_role(role: HvacRole) -> list[str]:
        return sorted(
            [device_id for device_id, profile in profiles.items() if profile.roles & role],
            key=_device_sort_key,
        )

    terminals = ids_with_role(HvacRole.TERMINAL)
    terminal_primary = terminals[0] if terminals else None

    purifiers = ids_with_role(HvacRole.PURIFIER)
    purifier_command = None
    for device_id in purifiers:
        if profiles[device_id].roles & HvacRole.TERMINAL:
            purifier_command = device_id
            break
    if purifier_command is None and purifiers:
        purifier_command = purifiers[0]

    systems = ids_with_role(HvacRole.SYSTEM)
    schedulers = ids_with_role(HvacRole.SCHEDULER)

    terminal_keys: set[str] = set()
    for device_id in terminals:
        payload = hvac_raw.get(device_id)
        if isinstance(payload, dict):
            terminal_keys.update(payload.keys())

    zone_keys: set[str] = set()
    for state in (zone_state or {}).values():
        if isinstance(state, dict):
            zone_keys.update(state.keys())

    return HvacDiscovery(
        profiles=profiles,
        terminal_primary_id=terminal_primary,
        terminal_read_ids=tuple(terminals),
        purifier_command_id=purifier_command,
        purifier_read_ids=tuple(purifiers),
        system_id=systems[0] if systems else None,
        thermostat_ids=tuple(ids_with_role(HvacRole.THERMOSTAT)),
        actuator_ids=tuple(ids_with_role(HvacRole.ACTUATOR)),
        scheduler_id=schedulers[0] if schedulers else None,
        terminal_keys=frozenset(terminal_keys),
        zone_keys=frozenset(zone_keys),
    )


def resolve_terminal_state(
    hvac_raw: dict[str, dict[str, Any]],
    discovery: HvacDiscovery | None,
) -> tuple[dict[str, Any], str | None]:
    if not discovery or not discovery.terminal_read_ids:
        return {}, None
    for device_id in discovery.terminal_read_ids:
        payload = hvac_raw.get(device_id)
        if isinstance(payload, dict) and payload:
            return payload, device_id
    return {}, None


def resolve_purifier_state(
    hvac_raw: dict[str, dict[str, Any]],
    discovery: HvacDiscovery | None,
) -> tuple[dict[str, Any], str | None]:
    if not discovery or not discovery.purifier_read_ids:
        return {}, None
    for device_id in discovery.purifier_read_ids:
        payload = hvac_raw.get(device_id)
        if isinstance(payload, dict) and payload and "P_Mode" in payload:
            return payload, device_id
    return {}, None
