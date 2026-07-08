"""Repair issue helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


def issue_id_zones_empty(entry_id: str) -> str:
    return f"zones_empty_{entry_id}"


def async_create_zones_empty_issue(hass: HomeAssistant, entry: ConfigEntry) -> None:
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id_zones_empty(entry.entry_id),
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="zones_empty",
        translation_placeholders={"host": entry.data.get("host", "")},
    )


def async_delete_zones_empty_issue(hass: HomeAssistant, entry_id: str) -> None:
    ir.async_delete_issue(hass, DOMAIN, issue_id_zones_empty(entry_id))
