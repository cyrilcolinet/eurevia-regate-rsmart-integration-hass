"""GitHub label source of truth for reGATE device-telemetry issues.

Pure module (no Home Assistant imports) so `scripts/github_labels.py` can load
it to reconcile the repository's labels with what telemetry prefills.
"""

from __future__ import annotations

from typing import Any

TELEMETRY_BASE_LABEL = "device telemetry"
TELEMETRY_UNSUPPORTED_LABEL = "unsupported"
TELEMETRY_CAPABILITY_GAP_LABEL = "capability gap"

# (name, color hex without '#', description)
TELEMETRY_GITHUB_LABEL_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    (TELEMETRY_BASE_LABEL, "5319e7", "Anonymized device-telemetry report (opt-in)"),
    (TELEMETRY_UNSUPPORTED_LABEL, "b60205", "Device role not exposed in Home Assistant yet"),
    (TELEMETRY_CAPABILITY_GAP_LABEL, "d93f0b", "Known device with unmapped MQTT keys"),
)

# Old/renamed label names to delete from the repository during sync.
TELEMETRY_GITHUB_ORPHAN_LABELS: tuple[str, ...] = ("device-telemetry",)


def telemetry_github_labels(export: dict[str, Any]) -> list[str]:
    """Labels to prefill on the telemetry issue for a given profile export."""
    labels = [TELEMETRY_BASE_LABEL]
    if not export.get("supported_by_integration"):
        labels.append(TELEMETRY_UNSUPPORTED_LABEL)
    elif export.get("unknown_keys"):
        labels.append(TELEMETRY_CAPABILITY_GAP_LABEL)
    return labels
