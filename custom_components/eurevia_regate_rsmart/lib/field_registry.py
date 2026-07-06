"""Known MQTT field → Home Assistant sensor metadata."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfElectricPotential, UnitOfTemperature, UnitOfTime
from homeassistant.helpers.entity import EntityCategory

from .conversion import as_bool, as_float, as_int


@dataclass(frozen=True, slots=True)
class FieldSensorSpec:
    mqtt_key: str
    suffix: str
    translation_key: str
    device_class: SensorDeviceClass | None = None
    unit: str | None = None
    state_class: SensorStateClass | None = None
    entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC
    value_fn: Callable[[dict[str, Any]], Any] | None = None


def _str_field(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda state: str(state.get(key)).strip() if state.get(key) is not None else None


TERMINAL_FIELD_SPECS: tuple[FieldSensorSpec, ...] = (
    FieldSensorSpec(
        "Water_Temp",
        "water_temp",
        "terminal_water_temp",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
        None,
        lambda s: as_float(s.get("Water_Temp")),
    ),
    FieldSensorSpec(
        "Air_Temp",
        "air_temp",
        "terminal_air_temp",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
        None,
        lambda s: as_float(s.get("Air_Temp")),
    ),
    FieldSensorSpec(
        "Fan_Speed",
        "fan_speed",
        "terminal_fan_speed",
        None,
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
        None,
        lambda s: as_int(s.get("Fan_Speed")),
    ),
    FieldSensorSpec(
        "Valve_Cmd",
        "valve_cmd",
        "terminal_valve_cmd",
        None,
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
        None,
        lambda s: as_int(s.get("Valve_Cmd")),
    ),
    FieldSensorSpec(
        "Valve_Cmd_Corrected",
        "valve_cmd_corrected",
        "terminal_valve_cmd_corrected",
        None,
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
        None,
        lambda s: as_int(s.get("Valve_Cmd_Corrected")),
    ),
    FieldSensorSpec(
        "Mode",
        "mode_raw",
        "terminal_mode_raw",
        value_fn=lambda s: as_int(s.get("Mode")),
    ),
    FieldSensorSpec(
        "Fan_Mode",
        "fan_mode_raw",
        "terminal_fan_mode_raw",
        value_fn=lambda s: as_int(s.get("Fan_Mode")),
    ),
    FieldSensorSpec(
        "Fan_Cmd",
        "fan_cmd_raw",
        "terminal_fan_cmd_raw",
        value_fn=lambda s: as_int(s.get("Fan_Cmd")),
    ),
    FieldSensorSpec(
        "Water_Hot",
        "water_hot_cfg",
        "terminal_water_hot_cfg",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        value_fn=lambda s: as_float(s.get("Water_Hot")),
    ),
    FieldSensorSpec(
        "Water_Cold",
        "water_cold_cfg",
        "terminal_water_cold_cfg",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        value_fn=lambda s: as_float(s.get("Water_Cold")),
    ),
    FieldSensorSpec(
        "Fan_Min",
        "fan_min_cfg",
        "terminal_fan_min_cfg",
        unit=PERCENTAGE,
        value_fn=lambda s: as_int(s.get("Fan_Min")),
    ),
    FieldSensorSpec(
        "Fan_Max",
        "fan_max_cfg",
        "terminal_fan_max_cfg",
        unit=PERCENTAGE,
        value_fn=lambda s: as_int(s.get("Fan_Max")),
    ),
    FieldSensorSpec("DB", "db_cfg", "terminal_db_cfg", value_fn=lambda s: as_float(s.get("DB"))),
    FieldSensorSpec(
        "Hyst", "hyst_cfg", "terminal_hyst_cfg", value_fn=lambda s: as_float(s.get("Hyst"))
    ),
    FieldSensorSpec(
        "PID_Enable",
        "pid_enable_cfg",
        "terminal_pid_enable_cfg",
        value_fn=lambda s: as_int(s.get("PID_Enable")),
    ),
    FieldSensorSpec(
        "PID_T_Integral",
        "pid_t_integral_cfg",
        "terminal_pid_t_integral_cfg",
        unit=UnitOfTime.SECONDS,
        value_fn=lambda s: as_int(s.get("PID_T_Integral")),
    ),
    FieldSensorSpec(
        "PID_T_Derivate",
        "pid_t_derivate_cfg",
        "terminal_pid_t_derivate_cfg",
        unit=UnitOfTime.SECONDS,
        value_fn=lambda s: as_int(s.get("PID_T_Derivate")),
    ),
    FieldSensorSpec(
        "P_Timer_Left",
        "p_timer_left",
        "terminal_p_timer_left",
        unit=UnitOfTime.MINUTES,
        value_fn=lambda s: as_int(s.get("P_Timer_Left")),
    ),
)

ZONE_FIELD_SPECS: tuple[FieldSensorSpec, ...] = (
    FieldSensorSpec(
        "RH",
        "humidity",
        "zone_humidity",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
        None,
        lambda s: as_float(s.get("RH")),
    ),
    FieldSensorSpec(
        "Battery",
        "battery_state",
        "zone_battery_state",
        value_fn=_str_field("Battery"),
    ),
    FieldSensorSpec(
        "Battery_low",
        "battery_low",
        "zone_battery_low",
        value_fn=lambda s: as_bool(s.get("Battery_low")),
    ),
    FieldSensorSpec(
        "Voltage",
        "voltage",
        "zone_voltage",
        unit=UnitOfElectricPotential.VOLT,
        value_fn=lambda s: as_float(s.get("Voltage")),
    ),
    FieldSensorSpec(
        "Voltage_percent",
        "voltage_percent",
        "zone_voltage_percent",
        unit=PERCENTAGE,
        value_fn=lambda s: as_int(s.get("Voltage_percent")),
    ),
    FieldSensorSpec("LQI", "lqi", "zone_lqi", value_fn=lambda s: as_int(s.get("LQI"))),
    FieldSensorSpec(
        "LQI_percent",
        "lqi_percent",
        "zone_lqi_percent",
        unit=PERCENTAGE,
        value_fn=lambda s: as_int(s.get("LQI_percent")),
    ),
    FieldSensorSpec("Com_Th", "com_th", "zone_com_th", value_fn=lambda s: as_bool(s.get("Com_Th"))),
    FieldSensorSpec(
        "Authorized",
        "authorized",
        "zone_authorized",
        value_fn=lambda s: as_bool(s.get("Authorized")),
    ),
    FieldSensorSpec(
        "Water_Auth",
        "water_auth",
        "zone_water_auth",
        value_fn=lambda s: as_bool(s.get("Water_Auth")),
    ),
    FieldSensorSpec(
        "Operating_Auth",
        "operating_auth",
        "zone_operating_auth",
        value_fn=lambda s: as_bool(s.get("Operating_Auth")),
    ),
    FieldSensorSpec("Demand", "demand", "zone_demand", value_fn=lambda s: as_bool(s.get("Demand"))),
    FieldSensorSpec(
        "SW_Version",
        "sw_version",
        "zone_sw_version",
        value_fn=_str_field("SW_Version"),
    ),
    FieldSensorSpec(
        "LQI_DATE",
        "lqi_date",
        "zone_lqi_date",
        value_fn=_str_field("LQI_DATE"),
    ),
)

TERMINAL_FIELD_SPECS_BY_KEY = {spec.mqtt_key: spec for spec in TERMINAL_FIELD_SPECS}
ZONE_FIELD_SPECS_BY_KEY = {spec.mqtt_key: spec for spec in ZONE_FIELD_SPECS}


def terminal_specs_for_keys(keys: frozenset[str] | set[str]) -> list[FieldSensorSpec]:
    return [TERMINAL_FIELD_SPECS_BY_KEY[key] for key in keys if key in TERMINAL_FIELD_SPECS_BY_KEY]


def zone_specs_for_keys(keys: frozenset[str] | set[str]) -> list[FieldSensorSpec]:
    return [ZONE_FIELD_SPECS_BY_KEY[key] for key in keys if key in ZONE_FIELD_SPECS_BY_KEY]
