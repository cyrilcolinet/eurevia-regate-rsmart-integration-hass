"""Integration-specific exceptions."""

from homeassistant.exceptions import HomeAssistantError


class CannotConnect(HomeAssistantError):
    """MQTT broker is unreachable."""


class MqttProtocolError(HomeAssistantError):
    """MQTT handshake or protocol error."""


class RegateNotFound(HomeAssistantError):
    """Broker reachable but no reGATE MQTT payload on the configured prefix."""


class MqttNotConnected(HomeAssistantError):
    """MQTT client is disconnected — command not sent."""
