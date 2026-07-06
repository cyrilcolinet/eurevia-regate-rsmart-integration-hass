"""End-to-end pipeline tests using frozen reGATE MQTT JSON snapshots."""

from __future__ import annotations

import pytest
from eurevia_regate_rsmart.lib.capabilities import HvacRole, discover_hvac_devices
from eurevia_regate_rsmart.lib.mapping import (
    build_zone_cfg_from_zones_raw,
    compute_zone_mappings,
    is_thermostat_hvac_payload,
)
from eurevia_regate_rsmart.lib.setpoint_registry import setpoint_specs_for_keys
from eurevia_regate_rsmart.lib.setpoints import (
    MODE_COMFORT,
    MODE_ECO,
    MODE_REDUCED,
    read_active_setpoint,
    write_setpoint_payload,
)
from eurevia_regate_rsmart.lib.telemetry_profile import (
    profile_needs_telemetry,
    unknown_keys_for_profile,
)

pytestmark = pytest.mark.e2e


def test_snapshot_has_climatic_zones(regate_snapshot):
    zones = regate_snapshot["zones"]
    assert isinstance(zones, list)
    climatic = [zone for zone in zones if zone.get("isClimatic")]
    assert len(climatic) >= 3
    assert all(zone.get("devices") for zone in climatic)


def test_discovery_from_snapshot(hvac_raw):
    zone_state = {
        "sejour": hvac_raw["101"],
        "chambre": hvac_raw["102"],
        "bureau": hvac_raw["103"],
    }
    discovery = discover_hvac_devices(hvac_raw, zone_state)
    assert discovery.terminal_primary_id == "10"
    assert discovery.purifier_command_id == "10"
    assert set(discovery.terminal_read_ids) == {"10", "20"}
    assert set(discovery.thermostat_ids) == {"101", "102", "103"}
    assert discovery.system_id == "0"
    assert discovery.scheduler_id == "30"
    assert "Water_Temp" in discovery.terminal_keys
    assert "Stp_Eco_C" in discovery.zone_keys


def test_zone_mappings_from_snapshot(regate_snapshot, hvac_raw, hvac_id_to_th_id):
    zone_cfg = build_zone_cfg_from_zones_raw(regate_snapshot["zones"])
    th_id_to_zone_key, zone_key_to_hvac_id, zone_state = compute_zone_mappings(
        zone_cfg,
        regate_snapshot["zigbee_devices"],
        hvac_raw,
        hvac_id_to_th_id,
    )

    assert zone_key_to_hvac_id["sejour"] == "101"
    assert zone_key_to_hvac_id["chambre"] == "102"
    assert zone_key_to_hvac_id["bureau"] == "103"
    assert read_active_setpoint(zone_state["sejour"]) == 22.0
    assert read_active_setpoint(zone_state["chambre"]) == 16.0
    assert read_active_setpoint(zone_state["bureau"]) == 28.0


def test_setpoint_write_payloads_per_mode(hvac_raw):
    sejour = hvac_raw["101"]
    chambre = hvac_raw["102"]
    bureau = hvac_raw["103"]

    assert write_setpoint_payload(sejour, 21.0) == {"Mode": MODE_COMFORT, "Stp_Comf": 21.0}
    assert write_setpoint_payload(chambre, 17.0) == {"Mode": MODE_ECO, "Stp_Eco_H": 17.0}
    assert write_setpoint_payload(bureau, 26.0) == {"Mode": MODE_REDUCED, "Stp_Reduc_C": 26.0}


def test_number_entities_match_snapshot_keys(hvac_raw):
    discovery = discover_hvac_devices(hvac_raw, {"sejour": hvac_raw["101"]})
    specs = setpoint_specs_for_keys(discovery.zone_keys)
    mqtt_keys = {spec.mqtt_key for spec in specs}

    expected_keys = {
        "Stp_Comf",
        "Stp_Eco_C",
        "Stp_Eco_H",
        "Stp_Reduc_C",
        "Stp_Reduc_H",
        "Tmp_Offset",
    }
    assert expected_keys <= mqtt_keys


def test_placeholder_thermostat_not_classified(hvac_raw):
    payload = hvac_raw["104"]
    assert not is_thermostat_hvac_payload(payload)


def test_telemetry_flags_from_snapshot(hvac_raw):
    discovery = discover_hvac_devices(hvac_raw)
    profiles_by_id = {profile.device_id: profile for profile in discovery.profiles.values()}

    system_unknown = unknown_keys_for_profile(profiles_by_id["0"])
    assert profile_needs_telemetry(profiles_by_id["0"], system_unknown) is False

    sejour_unknown = unknown_keys_for_profile(profiles_by_id["101"])
    assert profile_needs_telemetry(profiles_by_id["101"], sejour_unknown) is False

    scheduler_profile = profiles_by_id["30"]
    assert scheduler_profile.roles & HvacRole.SCHEDULER
    assert profile_needs_telemetry(
        scheduler_profile, unknown_keys_for_profile(scheduler_profile)
    ) is False
