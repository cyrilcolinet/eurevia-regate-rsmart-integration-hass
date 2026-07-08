"""Repair issue helpers."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


def issue_id_zones_empty(entry_id: str) -> str:
    return f"zones_empty_{entry_id}"


def issue_id_mqtt_disconnected(entry_id: str) -> str:
    return f"mqtt_disconnected_{entry_id}"


def issue_id_mqtt_stale(entry_id: str) -> str:
    return f"mqtt_stale_{entry_id}"


def issue_id_unsupported_profile(entry_id: str, fingerprint: str) -> str:
    return f"unsupported_profile_{entry_id}_{fingerprint[:16]}"


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


def async_create_mqtt_disconnected_issue(hass: HomeAssistant, entry: ConfigEntry) -> None:
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id_mqtt_disconnected(entry.entry_id),
        is_fixable=True,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.ERROR,
        translation_key="mqtt_disconnected",
        translation_placeholders={"host": entry.data.get("host", "")},
    )


def async_delete_mqtt_disconnected_issue(hass: HomeAssistant, entry_id: str) -> None:
    ir.async_delete_issue(hass, DOMAIN, issue_id_mqtt_disconnected(entry_id))


def async_create_mqtt_stale_issue(hass: HomeAssistant, entry: ConfigEntry) -> None:
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id_mqtt_stale(entry.entry_id),
        is_fixable=False,
        issue_domain=DOMAIN,
        severity=ir.IssueSeverity.WARNING,
        translation_key="mqtt_stale",
        translation_placeholders={"host": entry.data.get("host", "")},
    )


def async_delete_mqtt_stale_issue(hass: HomeAssistant, entry_id: str) -> None:
    ir.async_delete_issue(hass, DOMAIN, issue_id_mqtt_stale(entry_id))


def async_sync_unsupported_profile_issues(
    hass: HomeAssistant,
    entry: ConfigEntry,
    profiles: list[tuple[str, str]],
) -> None:
    """Create repair issues for unsupported profiles (fingerprint, role_label)."""
    active_ids = {issue_id_unsupported_profile(entry.entry_id, fp) for fp, _ in profiles}
    for fingerprint, role_label in profiles:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id_unsupported_profile(entry.entry_id, fingerprint),
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.WARNING,
            translation_key="unsupported_profile",
            translation_placeholders={"roles": role_label},
        )
    registry = ir.async_get(hass)
    prefix = f"unsupported_profile_{entry.entry_id}_"
    for issue in registry.issues.values():
        if issue.domain != DOMAIN or not issue.issue_id.startswith(prefix):
            continue
        if issue.issue_id not in active_ids:
            ir.async_delete_issue(hass, DOMAIN, issue.issue_id)


def async_clear_unsupported_profile_issues(hass: HomeAssistant, entry_id: str) -> None:
    registry = ir.async_get(hass)
    prefix = f"unsupported_profile_{entry_id}_"
    for issue in list(registry.issues.values()):
        if issue.domain == DOMAIN and issue.issue_id.startswith(prefix):
            ir.async_delete_issue(hass, DOMAIN, issue.issue_id)


def async_clear_all_entry_issues(hass: HomeAssistant, entry_id: str) -> None:
    async_delete_zones_empty_issue(hass, entry_id)
    async_delete_mqtt_disconnected_issue(hass, entry_id)
    async_delete_mqtt_stale_issue(hass, entry_id)
    async_clear_unsupported_profile_issues(hass, entry_id)
