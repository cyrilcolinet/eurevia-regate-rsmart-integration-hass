"""Integration-specific exceptions."""

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN


class CannotConnect(HomeAssistantError):
    """MQTT broker is unreachable."""


class MqttProtocolError(HomeAssistantError):
    """MQTT handshake or protocol error."""


class RegateNotFound(HomeAssistantError):
    """Broker reachable but no reGATE MQTT payload on the configured prefix."""


class MqttNotConnected(HomeAssistantError):
    """MQTT client is disconnected — command not sent."""

    def __init__(self, translation_key: str = "mqtt_not_connected") -> None:
        super().__init__(translation_domain=DOMAIN, translation_key=translation_key)
