"""Opt-in HVAC profile notifications (pre-filled GitHub issue link)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..const import CONF_TELEMETRY, DOMAIN, LOGGER
from ..lib.capabilities import HvacDiscovery
from ..lib.telemetry_profile import (
    build_github_new_issue_url,
    is_placeholder_thermostat,
    profile_fingerprint,
    profile_needs_telemetry,
    profile_should_raise_repair_issue,
    profile_to_export_dict,
    repair_role_label_for_profile,
    unknown_keys_for_profile,
)
from ..repair import async_clear_unsupported_profile_issues, async_sync_unsupported_profile_issues

STORAGE_VERSION = 1

_LOGGER = logging.getLogger(LOGGER)


class EureviaTelemetryReporter:
    """Notify once per new anonymized HVAC profile (manual GitHub issue)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.telemetry.{entry.entry_id}",
        )
        self._reported: set[str] | None = None

    async def async_report(
        self,
        discovery: HvacDiscovery,
        hvac_raw: dict[str, dict[str, Any]],
    ) -> None:
        if not self._entry.options.get(CONF_TELEMETRY, False):
            async_clear_unsupported_profile_issues(self._hass, self._entry.entry_id)
            return
        if not discovery.profiles:
            return

        reported = await self._load_reported()
        integration_version = _integration_version()
        ha_version = _ha_version(self._hass)
        new_count = 0
        unsupported_repairs: list[tuple[str, str]] = []

        for profile in discovery.profiles.values():
            if is_placeholder_thermostat(profile, hvac_raw):
                continue

            unknown_keys = unknown_keys_for_profile(profile)
            try:
                export_dict = profile_to_export_dict(
                    profile,
                    unknown_keys=unknown_keys,
                    integration_version=integration_version,
                    ha_version=ha_version,
                )
                fingerprint = profile_fingerprint(export_dict)
            except (TypeError, ValueError) as err:
                _LOGGER.warning(
                    "Skipping telemetry for HVAC profile roles=%s: %s",
                    profile.roles,
                    err,
                )
                continue

            needs_telemetry = profile_needs_telemetry(profile, unknown_keys)

            if profile_should_raise_repair_issue(profile, unknown_keys):
                role_label = repair_role_label_for_profile(profile)
                unsupported_repairs.append((fingerprint, role_label))

            if fingerprint in reported:
                if not needs_telemetry:
                    self._dismiss_profile_notification(fingerprint)
                continue

            if not needs_telemetry:
                reported.add(fingerprint)
                await self._save_reported(reported)
                continue

            new_count += 1
            self._notify_new_profile(export_dict, fingerprint)
            reported.add(fingerprint)
            await self._save_reported(reported)

        async_sync_unsupported_profile_issues(self._hass, self._entry, unsupported_repairs)

        if new_count:
            _LOGGER.info(
                "Notified about %s new reGATE HVAC profile(s) (opt-in telemetry)",
                new_count,
            )

    def _dismiss_profile_notification(self, fingerprint: str) -> None:
        persistent_notification.async_dismiss(
            self._hass,
            notification_id=f"{DOMAIN}_profile_{fingerprint[:16]}",
        )

    def _notify_new_profile(self, export_dict: dict[str, Any], fingerprint: str) -> None:
        roles = export_dict.get("roles") or ["unknown"]
        role_label = ", ".join(roles)
        issue_url = build_github_new_issue_url(export_dict, fingerprint)
        supported = export_dict.get("supported_by_integration")
        title, message = _profile_notification_copy(
            self._hass,
            role_label=role_label,
            issue_url=issue_url,
            supported=bool(supported),
        )
        persistent_notification.async_create(
            self._hass,
            message=message,
            title=title,
            notification_id=f"{DOMAIN}_profile_{fingerprint[:16]}",
        )

    async def _load_reported(self) -> set[str]:
        if self._reported is not None:
            return self._reported
        data = await self._store.async_load() or {}
        fingerprints = data.get("fingerprints") or []
        if not isinstance(fingerprints, list):
            fingerprints = []
        self._reported = {str(item) for item in fingerprints if item}
        return self._reported

    async def _save_reported(self, reported: set[str]) -> None:
        self._reported = reported
        await self._store.async_save({"fingerprints": sorted(reported)})


def _integration_version() -> str:
    from .. import __version__

    return __version__


def _ha_version(hass: HomeAssistant) -> str:
    version = getattr(hass.config, "version", None)
    return str(version) if version is not None else "unknown"


def _profile_notification_copy(
    hass: HomeAssistant,
    *,
    role_label: str,
    issue_url: str,
    supported: bool,
) -> tuple[str, str]:
    language = getattr(hass.config, "language", None) or "en"
    if language.startswith("fr"):
        if supported:
            return (
                "Eurevia reGATE — nouveau profil MQTT",
                (
                    f"Profil détecté : **{role_label}**.\n\n"
                    "Clés MQTT anonymisées — rien n'est envoyé sans votre action.\n\n"
                    f"[Ouvrir une issue GitHub pré-remplie]({issue_url})"
                ),
            )
        return (
            "Eurevia reGATE — profil non supporté",
            (
                f"Rôles **{role_label}** pas encore gérés par l'intégration.\n\n"
                f"[Proposer le support sur GitHub]({issue_url})"
            ),
        )

    if supported:
        return (
            "Eurevia reGATE — new MQTT profile",
            (
                f"Profile detected: **{role_label}**.\n\n"
                "Anonymized MQTT key names only — nothing is sent without your action.\n\n"
                f"[Open a pre-filled GitHub issue]({issue_url})"
            ),
        )
    return (
        "Eurevia reGATE — unsupported profile",
        (
            f"Roles **{role_label}** are not supported by the integration yet.\n\n"
            f"[Request support on GitHub]({issue_url})"
        ),
    )
