"""Eurevia reGATE (rSmart) Home Assistant integration."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_PREFIX,
    CONF_ZONES,
    DOMAIN,
    LOGGER,
    SIGNAL_DISCOVERY_UPDATED,
    SIGNAL_HVAC_DEVICE_STATE_UPDATED,
    SIGNAL_ZONE_STATE_UPDATED,
    SIGNAL_ZONES_UPDATED,
    parse_hvac_device_id,
    topic_hvac_devices,
    topic_zigbee_devices,
    topic_zones,
)
from .lib import (
    build_zone_cfg_from_zones_raw,
    compute_zone_mappings,
    discover_hvac_devices,
    is_thermostat_hvac_payload,
    normalize_th_id,
)
from .mqtt import MqttConnInfo, SimpleMqttClient

_LOGGER = logging.getLogger(LOGGER)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.FAN,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
]

__version__ = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))[
    "version"
]

type EureviaRegateConfigEntry = ConfigEntry


def _empty_discovery():
    return discover_hvac_devices({})


def _select_zone_cfg(entry: ConfigEntry, zones_raw: list[dict[str, Any]]) -> dict[str, dict]:
    zones_opt = dict(entry.options.get(CONF_ZONES, {}))
    if zones_opt:
        return zones_opt
    return build_zone_cfg_from_zones_raw(zones_raw)


async def async_setup_entry(hass: HomeAssistant, entry: EureviaRegateConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = int(entry.data[CONF_PORT])
    prefix = entry.data[CONF_PREFIX]

    store = hass.data.setdefault(DOMAIN, {}).setdefault(
        entry.entry_id,
        {
            "prefix": prefix,
            "client": None,
            "zones_raw": [],
            "zigbee_raw": None,
            "hvac_raw": {},
            "hvac_id_to_th_id": {},
            "zone_cfg": {},
            "th_id_to_zone_key": {},
            "zone_state": {},
            "zone_key_to_hvac_id": {},
            "discovery": _empty_discovery(),
        },
    )

    from .telemetry import EureviaTelemetryReporter, async_handle_telemetry_nudge

    telemetry = EureviaTelemetryReporter(hass, entry)
    store["telemetry"] = telemetry

    async def _report_telemetry() -> None:
        try:
            await telemetry.async_report(store["discovery"], store.get("hvac_raw") or {})
        except Exception:
            _LOGGER.warning("reGATE telemetry skipped after discovery update", exc_info=True)

    def recompute_all(*, notify_discovery: bool = True) -> None:
        zone_cfg = _select_zone_cfg(entry, store["zones_raw"])
        store["zone_cfg"] = zone_cfg

        th_id_to_zone_key, zone_key_to_hvac_id, zone_state = compute_zone_mappings(
            zone_cfg,
            store.get("zigbee_raw"),
            store.get("hvac_raw") or {},
            store.get("hvac_id_to_th_id") or {},
        )
        store["th_id_to_zone_key"] = th_id_to_zone_key
        store["zone_key_to_hvac_id"] = zone_key_to_hvac_id
        store["zone_state"] = zone_state

        previous = store.get("discovery")
        discovery = discover_hvac_devices(store.get("hvac_raw") or {}, zone_state)
        store["discovery"] = discovery

        async_dispatcher_send(hass, f"{SIGNAL_ZONES_UPDATED}_{entry.entry_id}")
        if notify_discovery and discovery != previous:
            async_dispatcher_send(hass, f"{SIGNAL_DISCOVERY_UPDATED}_{entry.entry_id}")
            hass.async_create_task(_report_telemetry())

    async def on_message(topic: str, payload: bytes) -> None:
        try:
            text = payload.decode("utf-8", errors="ignore")
        except Exception:
            return

        if topic == topic_zones(prefix):
            try:
                store["zones_raw"] = json.loads(text)
            except json.JSONDecodeError:
                store["zones_raw"] = []
            recompute_all()
            return

        if topic == topic_zigbee_devices(prefix):
            try:
                store["zigbee_raw"] = json.loads(text)
            except json.JSONDecodeError:
                store["zigbee_raw"] = None
            recompute_all()
            return

        hvac_id = parse_hvac_device_id(topic, prefix)
        if hvac_id is None:
            return

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return

        if not isinstance(data, dict):
            return

        store["hvac_raw"][hvac_id] = data
        async_dispatcher_send(hass, f"{SIGNAL_HVAC_DEVICE_STATE_UPDATED}_{entry.entry_id}", hvac_id)

        if is_thermostat_hvac_payload(data):
            th_id = normalize_th_id(data.get("Th_ID"))
            store["hvac_id_to_th_id"][hvac_id] = th_id

            zone_key = store["th_id_to_zone_key"].get(th_id)
            if not zone_key:
                recompute_all(notify_discovery=False)
                zone_key = store["th_id_to_zone_key"].get(th_id)
            if zone_key:
                store["zone_key_to_hvac_id"][zone_key] = hvac_id
                store["zone_state"][zone_key] = data
                async_dispatcher_send(
                    hass, f"{SIGNAL_ZONE_STATE_UPDATED}_{entry.entry_id}", zone_key
                )

        recompute_all()

    conn = MqttConnInfo(
        host=host,
        port=port,
        client_id=f"ha-regate-{uuid.uuid4().hex[:10]}",
        keepalive=30,
    )
    client = SimpleMqttClient(
        hass,
        conn,
        on_message,
        restart_max_attempts=3,
        restart_backoff_s=2.0,
        notification_id=f"{DOMAIN}_mqtt_{entry.entry_id}",
        notification_title="Eurevia reGATE MQTT",
    )
    store["client"] = client

    try:
        await client.start()
        await client.subscribe(topic_zones(prefix))
        await client.subscribe(topic_zigbee_devices(prefix))
        await client.subscribe(topic_hvac_devices(prefix))
    except Exception:
        _LOGGER.exception("MQTT startup failed")
        await client.stop()
        raise

    recompute_all()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_handle_telemetry_nudge(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EureviaRegateConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    store = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if store and store.get("client"):
        try:
            await store["client"].stop()
        except Exception:
            _LOGGER.debug("MQTT client stop failed", exc_info=True)

    if DOMAIN in hass.data and not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant,
    config_entry: EureviaRegateConfigEntry,
    device_entry,
) -> bool:
    return True
