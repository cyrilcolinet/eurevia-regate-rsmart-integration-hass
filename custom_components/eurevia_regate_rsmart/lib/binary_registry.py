"""Binary sensor specs for zone MQTT keys."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass


@dataclass(frozen=True, slots=True)
class BinarySensorSpec:
    mqtt_key: str
    suffix: str
    translation_key: str
    device_class: BinarySensorDeviceClass
    is_on_fn: Callable[[Any], bool | None]


def _window_is_on(value: Any) -> bool | None:
    if value is None:
        return None
    return str(value).lower() == "open"


def _presence_is_on(value: Any) -> bool | None:
    if value is None:
        return None
    return str(value).lower() == "presence"


ZONE_BINARY_SPECS: tuple[BinarySensorSpec, ...] = (
    BinarySensorSpec(
        "Window",
        "window",
        "window",
        BinarySensorDeviceClass.WINDOW,
        _window_is_on,
    ),
    BinarySensorSpec(
        "Detection",
        "presence",
        "presence",
        BinarySensorDeviceClass.OCCUPANCY,
        _presence_is_on,
    ),
)

ZONE_BINARY_SPECS_BY_KEY = {spec.mqtt_key: spec for spec in ZONE_BINARY_SPECS}
