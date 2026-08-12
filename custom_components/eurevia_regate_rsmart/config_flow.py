"""Config flow for Eurevia reGATE (rSmart)."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_PREFIX,
    CONF_TELEMETRY,
    CONF_TELEMETRY_ONBOARDING,
    DEFAULT_PORT,
    DEFAULT_PREFIX,
    DOMAIN,
    LOGGER,
    topic_zones,
)
from .exceptions import CannotConnect, MqttProtocolError, RegateNotFound
from .mqtt import MqttConnInfo, SimpleMqttClient

_LOGGER = logging.getLogger(LOGGER)


def _connection_schema(host: str | None, port: int, prefix: str) -> vol.Schema:
    host_field = vol.Required(CONF_HOST) if host is None else vol.Required(CONF_HOST, default=host)
    return vol.Schema(
        {
            host_field: str,
            vol.Optional(CONF_PORT, default=port): int,
            vol.Optional(CONF_PREFIX, default=prefix): str,
        }
    )


class EureviaRegateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_connection_schema(None, DEFAULT_PORT, DEFAULT_PREFIX),
            )

        host = user_input[CONF_HOST].strip()
        port = int(user_input[CONF_PORT])
        prefix = (user_input.get(CONF_PREFIX) or DEFAULT_PREFIX).strip("/") or DEFAULT_PREFIX

        await self.async_set_unique_id(f"{DOMAIN}_{host}_{port}_{prefix}")
        self._abort_if_unique_id_configured()

        errors = await self._validate_connection(host, port, prefix)
        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=_connection_schema(host, port, prefix),
                errors=errors,
            )

        self.context["connection"] = {
            CONF_HOST: host,
            CONF_PORT: port,
            CONF_PREFIX: prefix,
        }
        return await self.async_step_telemetry()

    async def async_step_reconfigure(self, user_input: dict | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()

        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=_connection_schema(
                    entry.data.get(CONF_HOST),
                    int(entry.data.get(CONF_PORT, DEFAULT_PORT)),
                    entry.data.get(CONF_PREFIX, DEFAULT_PREFIX),
                ),
            )

        host = user_input[CONF_HOST].strip()
        port = int(user_input[CONF_PORT])
        prefix = (user_input.get(CONF_PREFIX) or DEFAULT_PREFIX).strip("/") or DEFAULT_PREFIX

        errors = await self._validate_connection(host, port, prefix)
        if errors:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=_connection_schema(host, port, prefix),
                errors=errors,
            )

        return self.async_update_reload_and_abort(
            entry,
            unique_id=f"{DOMAIN}_{host}_{port}_{prefix}",
            data_updates={
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_PREFIX: prefix,
            },
        )

    async def _validate_connection(self, host: str, port: int, prefix: str) -> dict[str, str]:
        try:
            await self._validate_broker(host, port, prefix)
        except CannotConnect:
            return {"base": "cannot_connect"}
        except MqttProtocolError:
            return {"base": "invalid_mqtt"}
        except RegateNotFound:
            return {"base": "regate_not_found"}
        except Exception:
            _LOGGER.exception("Unexpected error during broker validation")
            return {"base": "unknown"}
        return {}

    async def async_step_telemetry(self, user_input: dict | None = None) -> ConfigFlowResult:
        connection = self.context.get("connection")
        if not connection:
            return await self.async_step_user()

        if user_input is not None:
            host = connection[CONF_HOST]
            port = int(connection[CONF_PORT])
            return self.async_create_entry(
                title=f"reGATE {host}:{port}",
                data=connection,
                options={
                    CONF_TELEMETRY: user_input[CONF_TELEMETRY],
                    CONF_TELEMETRY_ONBOARDING: True,
                },
            )

        return self.async_show_form(
            step_id="telemetry",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TELEMETRY, default=False): selector.BooleanSelector(),
                }
            ),
        )

    async def _validate_broker(self, host: str, port: int, prefix: str) -> None:
        try:
            _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5)
        except OSError as exc:
            raise CannotConnect(str(exc)) from exc

        writer.close()
        await writer.wait_closed()

        zones_event = asyncio.Event()
        zones_valid = False

        async def _on_probe_message(topic: str, payload: bytes) -> None:
            nonlocal zones_valid
            if topic != topic_zones(prefix):
                return
            try:
                data = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError:
                return
            if isinstance(data, list):
                zones_valid = True
                zones_event.set()

        probe_client: SimpleMqttClient | None = None
        conn = MqttConnInfo(
            host=host,
            port=port,
            client_id=f"ha-regate-probe-{uuid.uuid4().hex[:8]}",
            keepalive=10,
        )
        probe_client = SimpleMqttClient(
            self.hass,
            conn,
            _on_probe_message,
            restart_max_attempts=2,
        )
        try:
            await probe_client.start()
            await probe_client.subscribe(topic_zones(prefix))
            try:
                await asyncio.wait_for(zones_event.wait(), timeout=8.0)
            except TimeoutError as exc:
                raise RegateNotFound(
                    f"No reGATE zones payload on topic {topic_zones(prefix)}"
                ) from exc
            if not zones_valid:
                raise RegateNotFound(f"Invalid reGATE zones payload on {topic_zones(prefix)}")
        except ConnectionError as exc:
            raise MqttProtocolError(str(exc)) from exc
        finally:
            if probe_client:
                await probe_client.stop()

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        from .options_flow import EureviaRegateOptionsFlowHandler

        return EureviaRegateOptionsFlowHandler(config_entry)
