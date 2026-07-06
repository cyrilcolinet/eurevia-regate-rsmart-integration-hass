"""Fixtures for JSON snapshot end-to-end tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
DEFAULT_SNAPSHOT = FIXTURES_DIR / "regate_snapshot.json"


def load_regate_snapshot(path: Path = DEFAULT_SNAPSHOT) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def regate_snapshot() -> dict[str, Any]:
    return load_regate_snapshot()


@pytest.fixture(scope="module")
def hvac_raw(regate_snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(regate_snapshot["hvac_devices"])


@pytest.fixture(scope="module")
def hvac_id_to_th_id(hvac_raw: dict[str, dict[str, Any]]) -> dict[str, str]:
    from eurevia_regate_rsmart.lib.mapping import is_thermostat_hvac_payload, normalize_th_id

    mapping: dict[str, str] = {}
    for device_id, payload in hvac_raw.items():
        if is_thermostat_hvac_payload(payload):
            mapping[device_id] = normalize_th_id(payload.get("Th_ID"))
    return mapping
