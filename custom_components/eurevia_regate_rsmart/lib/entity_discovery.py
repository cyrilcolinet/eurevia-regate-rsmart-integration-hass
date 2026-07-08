"""Pure helpers for deciding which dynamic entities to create."""

from __future__ import annotations

from .field_registry import FieldSensorSpec, terminal_specs_for_keys, zone_specs_for_keys
from .setpoint_registry import SetpointNumberSpec, setpoint_specs_for_keys


def zone_entity_cache_key(zone_key: str, suffix: str) -> str:
    return f"{zone_key}:{suffix}"


def terminal_sensor_specs_for_discovery(
    terminal_keys: frozenset[str] | set[str],
) -> list[FieldSensorSpec]:
    return terminal_specs_for_keys(terminal_keys)


def zone_sensor_specs_for_zone(
    zone_key: str,
    zone_state: dict,
    zone_field_keys: frozenset[str] | set[str],
) -> list[FieldSensorSpec]:
    specs = zone_specs_for_keys(zone_field_keys)
    return [spec for spec in specs if spec.mqtt_key in zone_state]


def zone_number_specs_for_zone(
    zone_key: str,
    zone_state: dict,
    zone_field_keys: frozenset[str] | set[str],
) -> list[SetpointNumberSpec]:
    specs = setpoint_specs_for_keys(zone_field_keys)
    return [spec for spec in specs if spec.mqtt_key in zone_state]
