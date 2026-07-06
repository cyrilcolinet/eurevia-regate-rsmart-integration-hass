"""One-time telemetry opt-in nudge for legacy installs (pre-1.1.0)."""

from __future__ import annotations

from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from ..const import CONF_TELEMETRY, CONF_TELEMETRY_ONBOARDING, DOMAIN, LOGGER

STORAGE_VERSION = 1
TELEMETRY_NUDGE_LEGACY_VERSION = "1.1.0"
NOTIFICATION_ID_PREFIX = f"{DOMAIN}_telemetry_nudge"


def parse_version(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for segment in version.replace("-", ".").split("."):
        if segment.isdigit():
            parts.append(int(segment))
        elif segment:
            break
    return tuple(parts or [0])


def version_is_before(version: str, reference: str) -> bool:
    left = parse_version(version)
    right = parse_version(reference)
    length = max(len(left), len(right))
    return left + (0,) * (length - len(left)) < right + (0,) * (length - len(right))


class EureviaTelemetryNudge:
    """Show a single settings notification encouraging telemetry for legacy users."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.install_meta.{entry.entry_id}",
        )

    async def async_handle_setup(self) -> None:
        meta = await self._load_meta()

        if self._entry.options.get(CONF_TELEMETRY):
            await self._dismiss_notification()
            if not meta.get("telemetry_nudge_dismissed"):
                meta["telemetry_nudge_dismissed"] = True
                await self._save_meta(meta)
            return

        if self._entry.options.get(CONF_TELEMETRY_ONBOARDING):
            meta.setdefault("first_seen_version", await self._integration_version())
            meta["telemetry_nudge_dismissed"] = True
            await self._save_meta(meta)
            return

        if meta.get("telemetry_nudge_dismissed"):
            return

        if not meta.get("first_seen_version"):
            meta["first_seen_version"] = "legacy"
            await self._save_meta(meta)

        if not self._should_nudge_legacy(meta):
            return

        await self._show_notification()
        meta["telemetry_nudge_dismissed"] = True
        await self._save_meta(meta)
        LOGGER.debug(
            "Showed one-time telemetry nudge for reGATE entry %s",
            self._entry.entry_id,
        )

    def _should_nudge_legacy(self, meta: dict[str, Any]) -> bool:
        first_seen = str(meta.get("first_seen_version", "legacy"))
        if first_seen == "legacy":
            return True
        return version_is_before(first_seen, TELEMETRY_NUDGE_LEGACY_VERSION)

    async def _show_notification(self) -> None:
        title, message = _nudge_copy(self._hass, self._entry.entry_id)
        persistent_notification.async_create(
            self._hass,
            message=message,
            title=title,
            notification_id=f"{NOTIFICATION_ID_PREFIX}_{self._entry.entry_id}",
        )

    async def _dismiss_notification(self) -> None:
        persistent_notification.async_dismiss(
            self._hass,
            f"{NOTIFICATION_ID_PREFIX}_{self._entry.entry_id}",
        )

    async def _load_meta(self) -> dict[str, Any]:
        return dict(await self._store.async_load() or {})

    async def _save_meta(self, meta: dict[str, Any]) -> None:
        await self._store.async_save(meta)

    async def _integration_version(self) -> str:
        from .. import __version__

        return __version__


def _nudge_copy(hass: HomeAssistant, entry_id: str) -> tuple[str, str]:
    configure_url = f"/config/integrations/configure/{entry_id}"
    if hass.config.language.startswith("fr"):
        return (
            "Eurevia reGATE — accélérez le support MQTT",
            (
                "Activez la **télémétrie opt-in** pour être averti lorsqu'un profil "
                "reGATE non supporté est détecté sur votre installation.\n\n"
                "Données **anonymisées** (rôles, noms de clés MQTT) — "
                "aucun envoi automatique, seulement un lien GitHub pré-rempli "
                "si vous le souhaitez.\n\n"
                "Cela aide à prioriser actionneurs, planificateurs et nouvelles clés MQTT.\n\n"
                f"[Ouvrir les options reGATE]({configure_url})"
            ),
        )
    return (
        "Eurevia reGATE — help prioritize MQTT support",
        (
            "Turn on **opt-in telemetry** to get notified when an unsupported reGATE "
            "MQTT profile is detected on your installation.\n\n"
            "**Anonymized** data only (roles, MQTT key names) — "
            "nothing is sent automatically; you get a pre-filled GitHub link if you choose.\n\n"
            "This helps prioritize actuators, schedulers, and new MQTT keys.\n\n"
            f"[Open reGATE options]({configure_url})"
        ),
    )


async def async_handle_telemetry_nudge(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await EureviaTelemetryNudge(hass, entry).async_handle_setup()
