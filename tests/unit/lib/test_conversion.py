"""Tests for type coercion helpers."""

from eurevia_regate_rsmart.lib.conversion import as_bool, as_float, as_int


def test_as_float_parses_numbers():
    assert as_float("21.5") == 21.5
    assert as_float(None) is None


def test_as_int_parses_and_defaults():
    assert as_int("3") == 3
    assert as_int(None, default=0) == 0


def test_as_bool_parses_common_values():
    assert as_bool("true") is True
    assert as_bool("off") is False
    assert as_bool(None) is None
