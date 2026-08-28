"""Tests for repair issue id helpers."""

from eurevia_regate_rsmart.repair import (
    issue_id_mqtt_disconnected,
    issue_id_mqtt_stale,
    issue_id_unsupported_profile,
    issue_id_zones_empty,
)


def test_issue_ids_are_stable():
    assert issue_id_zones_empty("abc") == "zones_empty_abc"
    assert issue_id_mqtt_disconnected("abc") == "mqtt_disconnected_abc"
    assert issue_id_mqtt_stale("abc") == "mqtt_stale_abc"
    assert issue_id_unsupported_profile("abc", "deadbeef" * 4) == (
        "unsupported_profile_abc_deadbeefdeadbeef"
    )
