"""Guard translation key parity across strings.json / en.json / fr.json.

Translations are kept in sync manually; this test fails on any key drift so a
new string in one file cannot ship without its translations.
"""

from __future__ import annotations

import json
from pathlib import Path

_COMPONENT = Path(__file__).resolve().parents[2] / "custom_components" / "eurevia_regate_rsmart"
_STRINGS = _COMPONENT / "strings.json"
_EN = _COMPONENT / "translations" / "en.json"
_FR = _COMPONENT / "translations" / "fr.json"


def _leaf_paths(node: object, prefix: str = "") -> set[str]:
    if isinstance(node, dict):
        paths: set[str] = set()
        for key, value in node.items():
            child = f"{prefix}.{key}" if prefix else key
            paths |= _leaf_paths(value, child)
        return paths
    return {prefix}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_strings_and_english_match() -> None:
    assert _leaf_paths(_load(_STRINGS)) == _leaf_paths(_load(_EN))


def test_english_and_french_match() -> None:
    assert _leaf_paths(_load(_EN)) == _leaf_paths(_load(_FR))
