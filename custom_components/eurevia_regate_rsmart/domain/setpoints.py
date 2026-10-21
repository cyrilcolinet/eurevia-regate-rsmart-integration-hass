"""Zone setpoint keys and active-target resolution from MQTT state."""

from __future__ import annotations

from typing import Any

from ..lib.conversion import as_float, as_int

MODE_OFF = 0
MODE_COMFORT = 1
MODE_ECO = 2
MODE_REDUCED = 3

WRITABLE_SETPOINT_KEYS = frozenset(
    {
        "Stp_Comf",
        "Stp_Comf_Min",
        "Stp_Comf_Max",
        "Stp_Eco_C",
        "Stp_Eco_H",
        "Stp_Reduc_C",
        "Stp_Reduc_H",
        "Tmp_Offset",
    }
)


def setpoint_key_for_mode(mode: int, *, heating: bool) -> str | None:
    if mode == MODE_COMFORT:
        return "Stp_Comf"
    if mode == MODE_ECO:
        return "Stp_Eco_H" if heating else "Stp_Eco_C"
    if mode == MODE_REDUCED:
        return "Stp_Reduc_H" if heating else "Stp_Reduc_C"
    return None


def read_active_setpoint(state: dict[str, Any], *, cooling_active: bool) -> float | None:
    mode = as_int(state.get("Mode"))
    if mode is None or mode == MODE_OFF:
        return None
    key = setpoint_key_for_mode(mode, heating=not cooling_active)
    if key is None:
        return None
    return as_float(state.get(key))


def resolve_zone_hvac_action(state: dict[str, Any], *, cooling_active: bool) -> str:
    mode = as_int(state.get("Mode"))
    if mode is None or mode == MODE_OFF:
        return "off"
    return "cool" if cooling_active else "heat"


def write_setpoint_payload(
    state: dict[str, Any],
    temperature: float,
    *,
    cooling_active: bool,
    mode: int | None = None,
) -> dict[str, Any]:
    resolved_mode = mode if mode is not None else as_int(state.get("Mode"))
    if resolved_mode is None or resolved_mode == MODE_OFF:
        resolved_mode = MODE_COMFORT
    key = setpoint_key_for_mode(resolved_mode, heating=not cooling_active)
    if key is None:
        key = "Stp_Comf"
        resolved_mode = MODE_COMFORT
    payload: dict[str, Any] = {key: temperature, "Mode": resolved_mode}
    return payload
