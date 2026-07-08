"""Tests for scheduler number registry."""

from eurevia_regate_rsmart.lib.scheduler_registry import scheduler_number_specs_for_keys


def test_scheduler_specs_from_snapshot_keys():
    specs = scheduler_number_specs_for_keys({"Day", "Night", "Stp", "Hyst", "Boost"})
    keys = {spec.mqtt_key for spec in specs}

    assert keys == {"Day", "Night", "Stp", "Hyst"}


def test_scheduler_specs_empty_when_no_scheduler_keys():
    assert scheduler_number_specs_for_keys({"Boost"}) == []
