"""Tests for the shared dynamic-entity dispatcher wiring."""

from unittest.mock import MagicMock

from eurevia_regate_rsmart.platforms.helpers import setup_dynamic_entities


def _setup():
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "entry"
    async_add_entities = MagicMock()
    build_entities = MagicMock(return_value=[])

    setup_dynamic_entities(hass, entry, async_add_entities, build_entities, ("signal",))
    # async_dispatcher_connect(hass, signal, _refresh) -> _refresh is 3rd arg
    import eurevia_regate_rsmart.platforms.helpers as helpers

    refresh = helpers.async_dispatcher_connect.call_args.args[2]
    return refresh, async_add_entities, build_entities


def test_refresh_ignores_dispatcher_payload():
    """Signals carrying a payload (e.g. hvac th_id) must not crash the callback."""
    refresh, async_add_entities, build_entities = _setup()

    async_add_entities.reset_mock()
    build_entities.reset_mock()

    # SIGNAL_HVAC_DEVICE_STATE_UPDATED is dispatched with a th_id argument.
    refresh("10")

    build_entities.assert_called_once_with()
    async_add_entities.assert_called_once()


def test_refresh_without_payload():
    """Signals sent without a payload keep working."""
    refresh, async_add_entities, build_entities = _setup()

    async_add_entities.reset_mock()
    build_entities.reset_mock()

    refresh()

    build_entities.assert_called_once_with()
    async_add_entities.assert_called_once()
