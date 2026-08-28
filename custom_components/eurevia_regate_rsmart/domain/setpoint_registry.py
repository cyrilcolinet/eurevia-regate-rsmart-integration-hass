"""Writable zone setpoint → Home Assistant number entity metadata."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory

from .setpoints import WRITABLE_SETPOINT_KEYS


@dataclass(frozen=True, slots=True)
class SetpointNumberSpec:
    mqtt_key: str
    suffix: str
    translation_key: str
    unit: str
    step: float
    entity_category: EntityCategory | None = EntityCategory.CONFIG


SETPOINT_NUMBER_SPECS: tuple[SetpointNumberSpec, ...] = (
    SetpointNumberSpec(
        "Stp_Comf", "stp_comf", "zone_stp_comf", UnitOfTemperature.CELSIUS, 0.5, None
    ),
    SetpointNumberSpec(
        "Stp_Comf_Min", "stp_comf_min", "zone_stp_comf_min", UnitOfTemperature.CELSIUS, 0.5, None
    ),
    SetpointNumberSpec(
        "Stp_Comf_Max", "stp_comf_max", "zone_stp_comf_max", UnitOfTemperature.CELSIUS, 0.5, None
    ),
    SetpointNumberSpec(
        "Stp_Eco_C", "stp_eco_c", "zone_stp_eco_c", UnitOfTemperature.CELSIUS, 0.5, None
    ),
    SetpointNumberSpec(
        "Stp_Eco_H", "stp_eco_h", "zone_stp_eco_h", UnitOfTemperature.CELSIUS, 0.5, None
    ),
    SetpointNumberSpec(
        "Stp_Reduc_C", "stp_reduc_c", "zone_stp_reduc_c", UnitOfTemperature.CELSIUS, 0.5, None
    ),
    SetpointNumberSpec(
        "Stp_Reduc_H", "stp_reduc_h", "zone_stp_reduc_h", UnitOfTemperature.CELSIUS, 0.5, None
    ),
    SetpointNumberSpec(
        "Tmp_Offset", "tmp_offset", "zone_tmp_offset", UnitOfTemperature.CELSIUS, 0.1, None
    ),
)

SETPOINT_SPECS_BY_KEY = {spec.mqtt_key: spec for spec in SETPOINT_NUMBER_SPECS}


def setpoint_specs_for_keys(keys: frozenset[str] | set[str]) -> list[SetpointNumberSpec]:
    allowed = WRITABLE_SETPOINT_KEYS & set(keys)
    return [spec for spec in SETPOINT_NUMBER_SPECS if spec.mqtt_key in allowed]
