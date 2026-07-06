"""Pure helpers for the Eurevia reGATE integration."""

from .capabilities import (
    HvacDeviceProfile,
    HvacDiscovery,
    HvacRole,
    classify_hvac_payload,
    discover_hvac_devices,
    resolve_purifier_state,
    resolve_terminal_state,
)
from .conversion import as_bool, as_float, as_int
from .mapping import (
    build_zone_cfg_from_zones_raw,
    compute_zone_mappings,
    is_thermostat_hvac_payload,
    normalize_th_id,
)
from .slugify import slugify_snake

__all__ = [
    "HvacDiscovery",
    "HvacDeviceProfile",
    "HvacRole",
    "as_bool",
    "as_float",
    "as_int",
    "build_zone_cfg_from_zones_raw",
    "classify_hvac_payload",
    "compute_zone_mappings",
    "discover_hvac_devices",
    "is_thermostat_hvac_payload",
    "normalize_th_id",
    "resolve_purifier_state",
    "resolve_terminal_state",
    "slugify_snake",
]
