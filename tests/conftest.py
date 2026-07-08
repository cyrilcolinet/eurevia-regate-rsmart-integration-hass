"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "custom_components"))

_HA_STUBS = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.dispatcher",
    "homeassistant.helpers.entity",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.event",
    "homeassistant.helpers.selector",
    "homeassistant.helpers.area_registry",
    "homeassistant.helpers.issue_registry",
    "homeassistant.helpers.storage",
    "homeassistant.components",
    "homeassistant.components.climate",
    "homeassistant.components.climate.const",
    "homeassistant.components.fan",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.number",
    "homeassistant.components.diagnostics",
    "homeassistant.components.persistent_notification",
]

for module_name in _HA_STUBS:
    sys.modules.setdefault(module_name, MagicMock())

_core = sys.modules["homeassistant.core"]
_core.callback = lambda fn: fn

_config_entries = sys.modules["homeassistant.config_entries"]
_config_entries.ConfigFlowResult = dict

_device_registry = sys.modules["homeassistant.helpers.device_registry"]
_device_registry.DeviceInfo = dict
