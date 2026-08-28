"""Validate the GitHub label source of truth and its telemetry parity."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_LABELS = _load(_ROOT / "scripts" / "github_labels.py", "regate_gh_labels")
_TELEMETRY = _load(
    _ROOT / "custom_components" / "eurevia_regate_rsmart" / "domain" / "telemetry_labels.py",
    "regate_telemetry_labels",
)


def test_definitions_are_valid_triples() -> None:
    for name, color, description in _LABELS.github_label_definitions():
        assert name and description
        assert len(color) == 6 and all(c in "0123456789abcdef" for c in color.lower())


def test_includes_core_labels() -> None:
    names = {name for name, _, _ in _LABELS.github_label_definitions()}
    assert {"device telemetry", "pending release", "released"} <= names


def test_orphans_include_legacy_name() -> None:
    assert "device-telemetry" in _LABELS.github_label_orphans()


def test_prefill_labels_are_all_defined() -> None:
    names = {name for name, _, _ in _LABELS.github_label_definitions()}
    exports = (
        {"supported_by_integration": False},
        {"supported_by_integration": True, "unknown_keys": ["X"]},
        {"supported_by_integration": True, "unknown_keys": []},
    )
    for export in exports:
        assert set(_TELEMETRY.telemetry_github_labels(export)) <= names
