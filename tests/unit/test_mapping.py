"""Tests for zone mapping logic."""

from eurevia_regate_rsmart.lib.mapping import (
    build_zone_cfg_from_zones_raw,
    compute_zone_mappings,
    is_thermostat_hvac_payload,
    thermostat_ieee_set,
)


def test_is_thermostat_hvac_payload_rejects_placeholder():
    payload = {"Mode": 1, "Stp_Comf": 20, "Tmp": 21, "Th_ID": "Th_ID"}
    assert is_thermostat_hvac_payload(payload) is False


def test_is_thermostat_hvac_payload_accepts_live_state():
    assert is_thermostat_hvac_payload(
        {"Mode": 1, "Stp_Comf": 20, "Tmp": 21, "Th_ID": "0xcafebabe11111111"}
    )


def test_build_zone_cfg_from_zones_raw_filters_non_climatic():
    zones = [
        {"id": 1, "name": "Séjour", "isClimatic": True, "devices": ["0"]},
        {"id": 2, "name": "Garage", "isClimatic": False, "devices": []},
    ]
    cfg = build_zone_cfg_from_zones_raw(zones)
    assert list(cfg.keys()) == ["sejour"]
    assert cfg["sejour"]["zone_id"] == 1


def test_thermostat_ieee_set_filters_zigbee_thermostats():
    payload = [
        {
            "deviceId": "0xcafebabe11111111",
            "deviceInfo": {"definition": {"model": "THERMOSTAT"}},
        },
        {"deviceId": "0xabc", "definition": {"model": "SWITCH"}},
    ]
    assert thermostat_ieee_set(payload) == {"0xcafebabe11111111"}


def test_compute_zone_mappings_links_hvac_to_zone():
    zone_cfg = {
        "sejour": {"zone_id": 1, "name": "Séjour", "devices": ["0"], "isClimatic": True},
        "zone_beta": {
            "zone_id": 2,
            "name": "Zone Beta",
            "devices": ["0xcafebabe11111111"],
            "isClimatic": True,
        },
    }
    hvac_raw = {
        "101": {"Mode": 1, "Stp_Comf": 22, "Tmp": 21, "Th_ID": "0"},
        "102": {"Mode": 0, "Stp_Comf": 20, "Tmp": 19, "Th_ID": "0xcafebabe11111111"},
    }
    hvac_id_to_th_id = {"101": "0", "102": "0xcafebabe11111111"}
    th_map, zone_hvac, zone_state = compute_zone_mappings(zone_cfg, [], hvac_raw, hvac_id_to_th_id)
    assert th_map["0"] == "sejour"
    assert zone_hvac["zone_beta"] == "102"
    assert zone_state["sejour"]["Tmp"] == 21
