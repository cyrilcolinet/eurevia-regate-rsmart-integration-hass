"""Pure helpers for MQTT connectivity observability."""

from __future__ import annotations

from datetime import datetime


def is_mqtt_stale(
    *,
    connected: bool,
    last_message_at: datetime | None,
    now: datetime,
    threshold_s: float,
) -> bool:
    if not connected or last_message_at is None:
        return False
    return (now - last_message_at).total_seconds() > threshold_s
