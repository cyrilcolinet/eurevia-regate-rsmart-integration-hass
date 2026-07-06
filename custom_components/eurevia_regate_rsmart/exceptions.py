"""Integration-specific exceptions."""

from homeassistant.exceptions import HomeAssistantError


class CannotConnect(HomeAssistantError):
    """MQTT broker is unreachable."""


class MqttProtocolError(HomeAssistantError):
    """MQTT handshake or protocol error."""
