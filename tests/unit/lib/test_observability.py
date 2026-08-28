"""Tests for MQTT observability helpers."""

from datetime import UTC, datetime, timedelta

from eurevia_regate_rsmart.lib.observability import is_mqtt_stale


def test_is_mqtt_stale_when_connected_but_silent():
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    last = now - timedelta(minutes=20)
    assert is_mqtt_stale(connected=True, last_message_at=last, now=now, threshold_s=900) is True


def test_is_mqtt_stale_false_when_recent_message():
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    last = now - timedelta(minutes=5)
    assert is_mqtt_stale(connected=True, last_message_at=last, now=now, threshold_s=900) is False


def test_is_mqtt_stale_false_when_disconnected():
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    last = now - timedelta(hours=1)
    assert is_mqtt_stale(connected=False, last_message_at=last, now=now, threshold_s=900) is False
