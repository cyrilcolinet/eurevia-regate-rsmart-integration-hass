"""Helpers to publish reGATE system device commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .system_registry import COOLING_PAC_VALUE, HEATING_PAC_VALUE

if TYPE_CHECKING:
    from ..store import RegateStore


async def async_apply_system_cooling(store: RegateStore, *, cooling: bool) -> None:
    from ..entity import async_publish_hvac_command

    discovery = store.discovery
    if not discovery or not discovery.system_id:
        return
    await async_publish_hvac_command(
        store,
        discovery.system_id,
        {"PAC": COOLING_PAC_VALUE if cooling else HEATING_PAC_VALUE},
    )
