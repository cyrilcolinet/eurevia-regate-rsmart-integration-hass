"""Writable HVAC scheduler device keys (reGATE device ~30)."""

from __future__ import annotations

from dataclasses import dataclass

SCHEDULER_NUMBER_KEYS = frozenset({"Day", "Night", "Stp", "Hyst"})


@dataclass(frozen=True, slots=True)
class SchedulerNumberSpec:
    mqtt_key: str
    suffix: str
    translation_key: str
    min_value: float
    max_value: float
    step: float
    unit: str | None = None


SCHEDULER_NUMBER_SPECS: tuple[SchedulerNumberSpec, ...] = (
    SchedulerNumberSpec("Day", "day", "scheduler_day", 0, 23, 1),
    SchedulerNumberSpec("Night", "night", "scheduler_night", 0, 23, 1),
    SchedulerNumberSpec("Stp", "setpoint", "scheduler_setpoint", 5, 35, 0.5, "°C"),
    SchedulerNumberSpec("Hyst", "hysteresis", "scheduler_hysteresis", 0, 5, 0.1, "°C"),
)


def scheduler_number_specs_for_keys(keys: frozenset[str] | set[str]) -> list[SchedulerNumberSpec]:
    return [spec for spec in SCHEDULER_NUMBER_SPECS if spec.mqtt_key in keys]
