"""Shared Home Assistant platform setup helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .store import RegateStore

EntityT = TypeVar("EntityT", bound=Entity)


def setup_dynamic_entities[EntityT: Entity](
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    build_entities: Callable[[], list[EntityT]],
    signal_names: tuple[str, ...],
) -> None:
    """Register entities once and re-run builder when dispatcher signals fire."""
    async_add_entities(build_entities(), update_before_add=False)

    @callback
    def _refresh() -> None:
        async_add_entities(build_entities(), update_before_add=False)

    for signal_name in signal_names:
        entry.async_on_unload(
            async_dispatcher_connect(hass, f"{signal_name}_{entry.entry_id}", _refresh)
        )


def zone_keys_from_store(store: RegateStore) -> list[str]:
    return list(store.zone_cfg.keys())
