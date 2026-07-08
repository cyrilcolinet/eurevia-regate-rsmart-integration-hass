"""Writable HVAC system device keys (reGATE device 0)."""

from __future__ import annotations

from dataclasses import dataclass

SYSTEM_NUMBER_KEYS = frozenset({"Heating_Mode", "PAC", "Mode"})

COOLING_PAC_VALUE = 1
HEATING_PAC_VALUE = 0


@dataclass(frozen=True, slots=True)
class SystemNumberSpec:
    mqtt_key: str
    suffix: str
    translation_key: str
    min_value: float
    max_value: float
    step: float


SYSTEM_NUMBER_SPECS: tuple[SystemNumberSpec, ...] = (
    SystemNumberSpec("Heating_Mode", "heating_mode", "system_heating_mode", 0, 3, 1),
    SystemNumberSpec("PAC", "pac", "system_pac", 0, 1, 1),
    SystemNumberSpec("Mode", "mode", "system_mode", 0, 3, 1),
)


def system_number_specs_for_keys(keys: frozenset[str] | set[str]) -> list[SystemNumberSpec]:
    return [spec for spec in SYSTEM_NUMBER_SPECS if spec.mqtt_key in keys]
