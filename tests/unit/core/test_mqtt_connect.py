"""Tests for the MQTT 3.1.1 CONNECT packet builder."""

from eurevia_regate_rsmart.mqtt.client import build_connect_packet

# Fixed var header: proto name "MQTT", level 4, <flags>, keepalive 30 (0x001e),
# then length-prefixed payload fields.
_ANON = b"\x10\x11\x00\x04MQTT\x04\x02\x00\x1e\x00\x05hello"


def test_anonymous_is_byte_identical():
    assert build_connect_packet("hello", 30) == _ANON


def test_password_without_username_stays_anonymous():
    # MQTT-3.1.2-22: a password requires a username.
    assert build_connect_packet("hello", 30, password="pass") == _ANON


def test_username_only():
    pkt = build_connect_packet("hello", 30, username="user")
    # flags 0x82 (username + clean session), remaining length 0x17 (17 + 6).
    assert pkt == b"\x10\x17\x00\x04MQTT\x04\x82\x00\x1e\x00\x05hello\x00\x04user"


def test_username_and_password():
    pkt = build_connect_packet("hello", 30, username="user", password="pass")
    # flags 0xc2 (username + password + clean session), remaining 0x1d (17 + 12).
    assert pkt == (b"\x10\x1d\x00\x04MQTT\x04\xc2\x00\x1e\x00\x05hello\x00\x04user\x00\x04pass")
