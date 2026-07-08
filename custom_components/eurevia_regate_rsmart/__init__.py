"""Eurevia reGATE (rSmart) Home Assistant integration."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_PREFIX,
    CONF_ZONES,
    DOMAIN,
    LOGGER,
    MQTT_DISCONNECTED_REPAIR_DELAY_S,
    MQTT_STALE_CHECK_INTERVAL_S,
    MQTT_STALE_THRESHOLD_S,
    SIGNAL_DISCOVERY_UPDATED,
    SIGNAL_HVAC_DEVICE_STATE_UPDATED,
    SIGNAL_MQTT_CONNECTION_CHANGED,
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
from .lib.observability import is_mqtt_stale
from .mqtt import MqttConnInfo, SimpleMqttClient
from .repair import (
    async_clear_all_entry_issues,
    async_create_mqtt_disconnected_issue,
    async_create_mqtt_stale_issue,
    async_create_zones_empty_issue,
    async_delete_mqtt_disconnected_issue,
    async_delete_mqtt_stale_issue,
    async_delete_zones_empty_issue,
)
from .store import RegateStore, cancel_scheduled_checks

_LOGGER = logging.getLogger(LOGGER)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.FAN,
    Platform.NUMBER,
]

__version__ = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))[
    "version"
]

type EureviaRegateConfigEntry = ConfigEntry

ZONES_EMPTY_CHECK_DELAY_S = 300


def _select_zone_cfg(entry: ConfigEntry, zones_raw: list[dict[str, Any]]) -> dict[str, dict]:
    zones_opt = dict(entry.options.get(CONF_ZONES, {}))
    if zones_opt:
        return zones_opt
    return build_zone_cfg_from_zones_raw(zones_raw)


async def async_setup_entry(hass: HomeAssistant, entry: EureviaRegateConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = int(entry.data[CONF_PORT])
    prefix = entry.data[CONF_PREFIX]

    store = RegateStore(prefix=prefix)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = store

    from .telemetry import EureviaTelemetryReporter, async_handle_telemetry_nudge

    store.telemetry = EureviaTelemetryReporter(hass, entry)

    async def _report_telemetry() -> None:
        try:
            await store.telemetry.async_report(store.discovery, store.hvac_raw)
        except Exception:
            _LOGGER.warning("reGATE telemetry skipped after discovery update", exc_info=True)

    def _set_mqtt_connected(connected: bool) -> None:
        if store.mqtt_connected == connected:
            return
        store.mqtt_connected = connected
        async_dispatcher_send(hass, f"{SIGNAL_MQTT_CONNECTION_CHANGED}_{entry.entry_id}")

    def _cancel_scheduled_checks() -> None:
        cancel_scheduled_checks(store)

    @callback
    def _on_mqtt_connected() -> None:
        _set_mqtt_connected(True)
        if store.client:
            store.client.dismiss_notification()
        store.mqtt_disconnect_notified = False
        _cancel_scheduled_checks()
        async_delete_zones_empty_issue(hass, entry.entry_id)
        async_delete_mqtt_disconnected_issue(hass, entry.entry_id)
        async_delete_mqtt_stale_issue(hass, entry.entry_id)
        _schedule_stale_check()

    @callback
    def _check_mqtt_disconnected_repair(_now) -> None:
        store.mqtt_disconnect_repair_unsub = None
        if store.mqtt_connected:
            return
        async_create_mqtt_disconnected_issue(hass, entry)

    @callback
    def _schedule_disconnect_repair() -> None:
        if store.mqtt_disconnect_repair_unsub:
            store.mqtt_disconnect_repair_unsub()
        store.mqtt_disconnect_repair_unsub = async_call_later(
            hass,
            MQTT_DISCONNECTED_REPAIR_DELAY_S,
            _check_mqtt_disconnected_repair,
        )

    @callback
    def _check_mqtt_stale(_now) -> None:
        store.mqtt_stale_check_unsub = None
        now = datetime.now(UTC)
        if is_mqtt_stale(
            connected=store.mqtt_connected,
            last_message_at=store.last_mqtt_message_at,
            now=now,
            threshold_s=MQTT_STALE_THRESHOLD_S,
        ):
            async_create_mqtt_stale_issue(hass, entry)
        _schedule_stale_check()

    @callback
    def _schedule_stale_check() -> None:
        if store.mqtt_stale_check_unsub:
            store.mqtt_stale_check_unsub()
        store.mqtt_stale_check_unsub = async_call_later(
            hass,
            MQTT_STALE_CHECK_INTERVAL_S,
            _check_mqtt_stale,
        )

    @callback
    def _on_mqtt_disconnected(reason: str) -> None:
        _set_mqtt_connected(False)
        if store.mqtt_disconnect_notified or store.client is None:
            return
        store.mqtt_disconnect_notified = True
        language = getattr(hass.config, "language", "en") or "en"
        if language.startswith("fr"):
            message = (
                "Connexion MQTT au reGATE perdue. Reconnexion automatique en cours.\n\n"
                f"Dernière erreur : {reason}"
            )
        else:
            message = (
                "MQTT connection to reGATE lost. Automatic reconnection in progress.\n\n"
                f"Last error: {reason}"
            )
        store.client._notify_ha(message)
        _schedule_disconnect_repair()

    def recompute_zone_mappings() -> bool:
        zone_cfg = _select_zone_cfg(entry, store.zones_raw)
        store.zone_cfg = zone_cfg

        th_id_to_zone_key, zone_key_to_hvac_id, zone_state = compute_zone_mappings(
            zone_cfg,
            store.zigbee_raw,
            store.hvac_raw,
            store.hvac_id_to_th_id,
        )
        changed = (
            th_id_to_zone_key != store.th_id_to_zone_key
            or zone_key_to_hvac_id != store.zone_key_to_hvac_id
            or zone_state != store.zone_state
        )
        store.th_id_to_zone_key = th_id_to_zone_key
        store.zone_key_to_hvac_id = zone_key_to_hvac_id
        store.zone_state = zone_state
        return changed

    def recompute_discovery(*, notify: bool = True) -> None:
        previous = store.discovery
        store.discovery = discover_hvac_devices(store.hvac_raw, store.zone_state)
        if notify and store.discovery != previous:
            async_dispatcher_send(hass, f"{SIGNAL_DISCOVERY_UPDATED}_{entry.entry_id}")
            hass.async_create_task(_report_telemetry())

    def recompute_all(*, notify_discovery: bool = True) -> None:
        mappings_changed = recompute_zone_mappings()
        recompute_discovery(notify=notify_discovery)
        if mappings_changed:
            async_dispatcher_send(hass, f"{SIGNAL_ZONES_UPDATED}_{entry.entry_id}")

    async def on_message(topic: str, payload: bytes) -> None:
        store.last_mqtt_message_at = datetime.now(UTC)
        async_delete_mqtt_stale_issue(hass, entry.entry_id)
        try:
            text = payload.decode("utf-8", errors="ignore")
        except Exception:
            _LOGGER.debug("MQTT payload decode failed for topic=%s", topic, exc_info=True)
            return

        if topic == topic_zones(prefix):
            try:
                store.zones_raw = json.loads(text)
            except json.JSONDecodeError:
                _LOGGER.debug("Invalid JSON on topic=%s", topic)
                store.zones_raw = []
            async_delete_zones_empty_issue(hass, entry.entry_id)
            recompute_all()
            return

        if topic == topic_zigbee_devices(prefix):
            try:
                parsed = json.loads(text)
                store.zigbee_raw = parsed if isinstance(parsed, list) else None
            except json.JSONDecodeError:
                _LOGGER.debug("Invalid JSON on topic=%s", topic)
                store.zigbee_raw = None
            recompute_all()
            return

        hvac_id = parse_hvac_device_id(topic, prefix)
        if hvac_id is None:
            return

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            _LOGGER.debug("Invalid JSON on topic=%s", topic)
            return

        if not isinstance(data, dict):
            return

        store.hvac_raw[hvac_id] = data
        async_dispatcher_send(hass, f"{SIGNAL_HVAC_DEVICE_STATE_UPDATED}_{entry.entry_id}", hvac_id)

        mapping_inputs_changed = False
        if is_thermostat_hvac_payload(data):
            th_id = normalize_th_id(data.get("Th_ID"))
            if store.hvac_id_to_th_id.get(hvac_id) != th_id:
                store.hvac_id_to_th_id[hvac_id] = th_id
                mapping_inputs_changed = True

            zone_key = store.th_id_to_zone_key.get(th_id)
            if not zone_key and mapping_inputs_changed:
                recompute_zone_mappings()
                zone_key = store.th_id_to_zone_key.get(th_id)

            if zone_key:
                store.zone_key_to_hvac_id[zone_key] = hvac_id
                store.zone_state[zone_key] = data
                async_dispatcher_send(
                    hass, f"{SIGNAL_ZONE_STATE_UPDATED}_{entry.entry_id}", zone_key
                )
                return

        if mapping_inputs_changed:
            recompute_all()
            return

        recompute_discovery()

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
        restart_max_attempts=None,
        restart_backoff_s=2.0,
        restart_backoff_cap_s=60.0,
        notification_id=f"{DOMAIN}_mqtt_{entry.entry_id}",
        notification_title="Eurevia reGATE MQTT",
        on_connected=_on_mqtt_connected,
        on_disconnected=_on_mqtt_disconnected,
    )
    store.client = client

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
    _set_mqtt_connected(client.is_connected)
    _schedule_stale_check()

    @callback
    def _check_zones_empty(_now) -> None:
        if store.zones_raw:
            return
        async_create_zones_empty_issue(hass, entry)

    async_call_later(hass, ZONES_EMPTY_CHECK_DELAY_S, _check_zones_empty)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_handle_telemetry_nudge(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EureviaRegateConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    store: RegateStore | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if store:
        cancel_scheduled_checks(store)
    async_clear_all_entry_issues(hass, entry.entry_id)
    if store and store.client:
        try:
            store.client.dismiss_notification()
            await store.client.stop()
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
