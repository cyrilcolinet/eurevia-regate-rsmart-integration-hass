"""Tests for HVAC publish helpers and MQTT availability."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from eurevia_regate_rsmart.entity import async_publish_hvac_command
from eurevia_regate_rsmart.exceptions import MqttNotConnected
from eurevia_regate_rsmart.store import RegateStore


@pytest.mark.asyncio
async def test_publish_raises_when_mqtt_disconnected():
    store = RegateStore(prefix="local", mqtt_connected=False)
    store.client = MagicMock()

    with pytest.raises(MqttNotConnected):
        await async_publish_hvac_command(store, "101", {"Mode": 1})


@pytest.mark.asyncio
async def test_publish_raises_when_client_publish_fails():
    store = RegateStore(prefix="local", mqtt_connected=True)
    client = MagicMock()
    client.publish = AsyncMock(side_effect=RuntimeError("MQTT writer not ready"))
    store.client = client

    with pytest.raises(MqttNotConnected):
        await async_publish_hvac_command(store, "101", {"Mode": 1})


@pytest.mark.asyncio
async def test_publish_succeeds_when_connected():
    store = RegateStore(prefix="local", mqtt_connected=True)
    client = MagicMock()
    client.publish = AsyncMock()
    store.client = client

    await async_publish_hvac_command(store, "101", {"Mode": 1})
    client.publish.assert_awaited_once()
