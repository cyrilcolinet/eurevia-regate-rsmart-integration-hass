"""Zone ↔ thermostat ↔ HVAC device mapping (pure logic, no HA imports)."""

from __future__ import annotations

from typing import Any

from .slugify import slugify_snake

PLACEHOLDER_TH_ID = "Th_ID"


def normalize_th_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_thermostat_hvac_payload(payload: dict[str, Any]) -> bool:
    """True when payload looks like a live zone thermostat state."""
    if not isinstance(payload, dict):
        return False
    if "Mode" not in payload or "Stp_Comf" not in payload or "Tmp" not in payload:
        return False
    th_id = normalize_th_id(payload.get("Th_ID"))
    return bool(th_id) and th_id != PLACEHOLDER_TH_ID


def thermostat_ieee_set(zigbee_devices_payload: Any) -> set[str]:
    out: set[str] = set()
    if not isinstance(zigbee_devices_payload, list):
        return out
    for device in zigbee_devices_payload:
        if not isinstance(device, dict):
            continue
        ieee = (
            device.get("ieee_address")
            or device.get("ieeeAddress")
            or device.get("ieee")
            or device.get("deviceId")
        )
        device_info = device.get("deviceInfo") or {}
        definition = device.get("definition") or device_info.get("definition") or {}
        model = (definition.get("model") or "").upper() if isinstance(definition, dict) else ""
        if ieee and model == "THERMOSTAT":
            out.add(str(ieee))
    return out


def build_zone_cfg_from_zones_raw(zones_raw: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for zone in zones_raw or []:
        if zone.get("isClimatic") is not True:
            continue
        zone_id = zone.get("id")
        if zone_id is None:
            continue
        name = zone.get("customName") or zone.get("name") or f"Zone {zone_id}"
        key = slugify_snake(name)
        out[key] = {
            "zone_id": int(zone_id),
            "name": name,
            "devices": list(zone.get("devices") or []),
            "isClimatic": True,
        }
    return out


def compute_zone_mappings(
    zone_cfg: dict[str, dict[str, Any]],
    zigbee_raw: Any,
    hvac_raw: dict[str, dict[str, Any]],
    hvac_id_to_th_id: dict[str, str],
) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, Any]]]:
    """Return th_id→zone_key, zone_key→hvac_id, zone_key→state."""
    th_id_to_zone_key: dict[str, str] = {}
    zigbee_thermo = thermostat_ieee_set(zigbee_raw)

    for zone_key, cfg in zone_cfg.items():
        devices = [str(item) for item in (cfg.get("devices") or [])]
        filtered: list[str] = []
        for dev in devices:
            if dev == "0":
                filtered.append(dev)
            elif dev.startswith("0x") and zigbee_thermo:
                if dev in zigbee_thermo:
                    filtered.append(dev)
            else:
                filtered.append(dev)

        for th_id in filtered:
            th_id_to_zone_key[normalize_th_id(th_id)] = zone_key

    zone_key_to_hvac_id: dict[str, str] = {}
    zone_state: dict[str, dict[str, Any]] = {}

    for hvac_id, th_id in hvac_id_to_th_id.items():
        zone_key = th_id_to_zone_key.get(normalize_th_id(th_id))
        if not zone_key:
            continue
        payload = hvac_raw.get(hvac_id)
        if not payload or not is_thermostat_hvac_payload(payload):
            continue
        zone_key_to_hvac_id[zone_key] = hvac_id
        zone_state[zone_key] = payload

    return th_id_to_zone_key, zone_key_to_hvac_id, zone_state
