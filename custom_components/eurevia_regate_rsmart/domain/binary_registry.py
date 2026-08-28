"""Zone binary-sensor specs derived from reGATE MQTT keys."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from ..lib.conversion import as_bool


@dataclass(frozen=True, slots=True)
class ZoneBinarySpec:
    mqtt_key: str
    suffix: str
    translation_key: str
    device_class: BinarySensorDeviceClass | None
    value_fn: Callable[[dict[str, Any]], bool | None]


ZONE_BINARY_SPECS: tuple[ZoneBinarySpec, ...] = (
    ZoneBinarySpec(
        mqtt_key="Window",
        suffix="zone_window",
        translation_key="zone_window",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda state: as_bool(state.get("Window")),
    ),
)


def zone_binary_specs_for_zone(zone_state: dict[str, Any]) -> list[ZoneBinarySpec]:
    """Specs for whichever binary keys are present in the zone payload."""
    return [spec for spec in ZONE_BINARY_SPECS if spec.mqtt_key in zone_state]
