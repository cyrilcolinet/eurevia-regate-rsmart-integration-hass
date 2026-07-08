"""Tests for telemetry reporter fingerprint persistence."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from eurevia_regate_rsmart.lib.capabilities import HvacDiscovery, classify_hvac_payload
from eurevia_regate_rsmart.lib.telemetry_profile import (
    profile_fingerprint,
    profile_to_export_dict,
    unknown_keys_for_profile,
)
from eurevia_regate_rsmart.telemetry.reporter import EureviaTelemetryReporter

ACTUATOR_PAYLOAD = {"Pos_Min": 0, "Pos_Max": 100, "Mystery": 1}
THERMO_PAYLOAD = {
    "Th_ID": "abc",
    "Mode": 1,
    "Tmp": 21.0,
    "Stp_Comf": 22.0,
    "Window": False,
}


@pytest.mark.asyncio
async def test_fingerprint_saved_after_notification():
    hass = MagicMock()
    hass.config.version = "2025.1.0"
    entry = MagicMock()
    entry.entry_id = "test"
    entry.options = {"telemetry": True}

    reporter = EureviaTelemetryReporter(hass, entry)
    reporter._store = MagicMock()
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})
    reporter._store.async_save = AsyncMock()
    reporter._notify_new_profile = MagicMock()

    profile = classify_hvac_payload("50", ACTUATOR_PAYLOAD)
    discovery = HvacDiscovery(
        profiles={"50": profile},
        terminal_primary_id=None,
        terminal_read_ids=(),
        purifier_command_id=None,
        purifier_read_ids=(),
        system_id=None,
        thermostat_ids=(),
        actuator_ids=("50",),
        scheduler_id=None,
        terminal_keys=frozenset(),
        zone_keys=frozenset(),
    )

    await reporter.async_report(discovery, {"50": ACTUATOR_PAYLOAD})

    reporter._notify_new_profile.assert_called_once()
    reporter._store.async_save.assert_called_once()


@pytest.mark.asyncio
async def test_supported_profile_fingerprint_saved_without_notification():
    hass = MagicMock()
    hass.config.version = "2025.1.0"
    entry = MagicMock()
    entry.entry_id = "test"
    entry.options = {"telemetry": True}

    reporter = EureviaTelemetryReporter(hass, entry)
    reporter._store = MagicMock()
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})
    reporter._store.async_save = AsyncMock()
    reporter._notify_new_profile = MagicMock()

    profile = classify_hvac_payload("101", THERMO_PAYLOAD)
    assert unknown_keys_for_profile(profile) == []
    discovery = HvacDiscovery(
        profiles={"101": profile},
        terminal_primary_id=None,
        terminal_read_ids=(),
        purifier_command_id=None,
        purifier_read_ids=(),
        system_id=None,
        thermostat_ids=("101",),
        actuator_ids=(),
        scheduler_id=None,
        terminal_keys=frozenset(),
        zone_keys=frozenset(),
    )

    await reporter.async_report(discovery, {"101": THERMO_PAYLOAD})

    reporter._notify_new_profile.assert_not_called()
    reporter._store.async_save.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_profile_does_not_notify_twice():
    hass = MagicMock()
    hass.config.version = "2025.1.0"
    entry = MagicMock()
    entry.entry_id = "test"
    entry.options = {"telemetry": True}

    reporter = EureviaTelemetryReporter(hass, entry)
    reporter._store = MagicMock()
    reporter._store.async_load = AsyncMock(return_value={"fingerprints": []})
    reporter._store.async_save = AsyncMock()
    reporter._notify_new_profile = MagicMock()

    profile = classify_hvac_payload("50", ACTUATOR_PAYLOAD)
    discovery = HvacDiscovery(
        profiles={"50": profile},
        terminal_primary_id=None,
        terminal_read_ids=(),
        purifier_command_id=None,
        purifier_read_ids=(),
        system_id=None,
        thermostat_ids=(),
        actuator_ids=("50",),
        scheduler_id=None,
        terminal_keys=frozenset(),
        zone_keys=frozenset(),
    )

    await reporter.async_report(discovery, {"50": ACTUATOR_PAYLOAD})
    await reporter.async_report(discovery, {"50": ACTUATOR_PAYLOAD})

    reporter._notify_new_profile.assert_called_once()


@pytest.mark.asyncio
async def test_supported_profile_dismisses_notification():
    hass = MagicMock()
    hass.config.version = "2025.1.0"
    entry = MagicMock()
    entry.entry_id = "test"
    entry.options = {"telemetry": True}

    reporter = EureviaTelemetryReporter(hass, entry)
    reporter._store = MagicMock()

    profile = classify_hvac_payload("101", THERMO_PAYLOAD)
    unknown = unknown_keys_for_profile(profile)
    export_dict = profile_to_export_dict(
        profile,
        unknown_keys=unknown,
        integration_version="1.2.1",
        ha_version="2025.1.0",
    )
    fingerprint = profile_fingerprint(export_dict)

    reporter._store.async_load = AsyncMock(return_value={"fingerprints": [fingerprint]})
    reporter._store.async_save = AsyncMock()
    reporter._dismiss_profile_notification = MagicMock()
    reporter._notify_new_profile = MagicMock()

    discovery = HvacDiscovery(
        profiles={"101": profile},
        terminal_primary_id=None,
        terminal_read_ids=(),
        purifier_command_id=None,
        purifier_read_ids=(),
        system_id=None,
        thermostat_ids=("101",),
        actuator_ids=(),
        scheduler_id=None,
        terminal_keys=frozenset(),
        zone_keys=frozenset(),
    )

    await reporter.async_report(discovery, {"101": THERMO_PAYLOAD})

    reporter._dismiss_profile_notification.assert_called_once()
    reporter._notify_new_profile.assert_not_called()
