"""Domain model for the Eurevia reGATE integration (pure, HA-free)."""

from .capabilities import (
    HvacDeviceProfile,
    HvacDiscovery,
    HvacRole,
    classify_hvac_payload,
    discover_hvac_devices,
    resolve_purifier_state,
    resolve_terminal_state,
)
from .mapping import (
    build_zone_cfg_from_zones_raw,
    compute_zone_mappings,
    is_thermostat_hvac_payload,
    normalize_th_id,
)

__all__ = [
    "HvacDeviceProfile",
    "HvacDiscovery",
    "HvacRole",
    "build_zone_cfg_from_zones_raw",
    "classify_hvac_payload",
    "compute_zone_mappings",
    "discover_hvac_devices",
    "is_thermostat_hvac_payload",
    "normalize_th_id",
    "resolve_purifier_state",
    "resolve_terminal_state",
]
