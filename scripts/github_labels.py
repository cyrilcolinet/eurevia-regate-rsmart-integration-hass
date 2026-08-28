#!/usr/bin/env python3
"""Source of truth for the repository's GitHub labels.

Merges the telemetry labels (loaded from the component's pure
`domain/telemetry_labels.py`, without importing Home Assistant) with the
release/triage workflow labels. Consumed by `sync_github_labels.sh`.

Run standalone to print the reconciliation plan:

    python3 scripts/github_labels.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_LABELS_MODULE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "eurevia_regate_rsmart"
    / "domain"
    / "telemetry_labels.py"
)


def _load_telemetry_labels():
    spec = importlib.util.spec_from_file_location("regate_telemetry_labels", _LABELS_MODULE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


_telemetry = _load_telemetry_labels()

# (name, color hex without '#', description)
WORKFLOW_GITHUB_LABEL_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("pending release", "0e8a16", "Merged and awaiting the next release"),
    ("released", "5319e7", "Shipped in a published release"),
    ("next release", "1d76db", "Planned for the next release"),
    ("release blocker", "b60205", "Must be resolved before releasing"),
    ("blocked", "d93f0b", "Blocked by an external dependency"),
    ("stale", "795548", "No activity for a while"),
    ("needs info", "fbca04", "Waiting on reporter details"),
    ("regression", "b60205", "Worked before, broken now"),
)


def github_label_definitions() -> tuple[tuple[str, str, str], ...]:
    return (*_telemetry.TELEMETRY_GITHUB_LABEL_DEFINITIONS, *WORKFLOW_GITHUB_LABEL_DEFINITIONS)


def github_label_orphans() -> tuple[str, ...]:
    return tuple(_telemetry.TELEMETRY_GITHUB_ORPHAN_LABELS)


def main() -> None:
    for name, color, description in github_label_definitions():
        print(f"upsert\t{name}\t{color}\t{description}")
    for name in github_label_orphans():
        print(f"delete\t{name}")


if __name__ == "__main__":
    main()
