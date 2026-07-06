"""Config flow for Eurevia reGATE (rSmart)."""

from __future__ import annotations

import asyncio
import logging
import uuid

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult

from .const import CONF_HOST, CONF_PORT, CONF_PREFIX, DEFAULT_PORT, DEFAULT_PREFIX, DOMAIN, LOGGER
from .exceptions import CannotConnect, MqttProtocolError
from .mqtt import MqttConnInfo, SimpleMqttClient

_LOGGER = logging.getLogger(LOGGER)


class EureviaRegateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                        vol.Optional(CONF_PREFIX, default=DEFAULT_PREFIX): str,
                    }
                ),
            )

        host = user_input[CONF_HOST].strip()
        port = int(user_input[CONF_PORT])
        prefix = (user_input.get(CONF_PREFIX) or DEFAULT_PREFIX).strip("/") or DEFAULT_PREFIX

        await self.async_set_unique_id(f"{DOMAIN}_{host}_{port}_{prefix}")
        self._abort_if_unique_id_configured()

        try:
            await self._validate_broker(host, port)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except MqttProtocolError:
            errors["base"] = "invalid_mqtt"
        except Exception:
            _LOGGER.exception("Unexpected error during broker validation")
            errors["base"] = "unknown"

        if errors:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_HOST, default=host): str,
                        vol.Optional(CONF_PORT, default=port): int,
                        vol.Optional(CONF_PREFIX, default=prefix): str,
                    }
                ),
                errors=errors,
            )

        return self.async_create_entry(
            title=f"reGATE {host}:{port}",
            data={CONF_HOST: host, CONF_PORT: port, CONF_PREFIX: prefix},
        )

    async def _validate_broker(self, host: str, port: int) -> None:
        try:
            _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5)
        except OSError as exc:
            raise CannotConnect(str(exc)) from exc

        writer.close()
        await writer.wait_closed()

        probe_client: SimpleMqttClient | None = None

        async def _noop(_topic: str, _payload: bytes) -> None:
            return

        conn = MqttConnInfo(
            host=host,
            port=port,
            client_id=f"ha-regate-probe-{uuid.uuid4().hex[:8]}",
            keepalive=10,
        )
        probe_client = SimpleMqttClient(self.hass, conn, _noop)
        try:
            await probe_client.start()
            await asyncio.sleep(0.5)
        except ConnectionError as exc:
            raise MqttProtocolError(str(exc)) from exc
        finally:
            if probe_client:
                await probe_client.stop()

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        from .options_flow import EureviaRegateOptionsFlowHandler

        return EureviaRegateOptionsFlowHandler(config_entry)
