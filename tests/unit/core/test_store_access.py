"""Regression guards for runtime-data store access."""

from __future__ import annotations

from types import SimpleNamespace

from eurevia_regate_rsmart.store import get_store


def test_get_store_reads_runtime_data() -> None:
    store = object()
    entry = SimpleNamespace(runtime_data=store)
    assert get_store(entry) is store


def test_get_store_none_when_runtime_data_missing() -> None:
    # A config entry whose setup failed has no runtime_data — callers must not crash.
    assert get_store(SimpleNamespace()) is None
