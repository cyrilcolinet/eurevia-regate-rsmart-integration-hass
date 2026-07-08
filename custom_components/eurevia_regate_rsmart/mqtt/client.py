from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

OnMessage = Callable[[str, bytes], Awaitable[None]]


def _enc_varint(n: int) -> bytes:
    out = bytearray()
    while True:
        digit = n % 128
        n //= 128
        if n > 0:
            digit |= 0x80
        out.append(digit)
        if n == 0:
            break
    return bytes(out)


def _pack_str(s: str) -> bytes:
    b = s.encode("utf-8")
    return len(b).to_bytes(2, "big") + b


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    return await reader.readexactly(n)


async def _read_varlen(reader: asyncio.StreamReader) -> int:
    multiplier = 1
    value = 0
    while True:
        digit = (await _read_exact(reader, 1))[0]
        value += (digit & 127) * multiplier
        if (digit & 128) == 0:
            break
        multiplier *= 128
        if multiplier > 128 * 128 * 128:
            raise ValueError("Malformed Remaining Length")
    return value


@dataclass
class MqttConnInfo:
    host: str
    port: int
    client_id: str
    keepalive: int = 30


class SimpleMqttClient:
    """
    Minimal MQTT 3.1.1 client (QoS0 only).
    Reads happen only in RX loop (no concurrent StreamReader reads).

    Features:
    - SUBSCRIBE QoS0
    - PUBLISH QoS0
    - keepalive PINGREQ
    - Auto-restart on crash/disconnect (infinite by default)
    - Optional max attempts for short-lived probes (config flow)
    - Persistent notification once per disconnect episode (via callbacks)
    """

    def __init__(
        self,
        hass: HomeAssistant,
        info: MqttConnInfo,
        on_message: OnMessage,
        *,
        restart_max_attempts: int | None = None,
        restart_backoff_s: float = 2.0,
        restart_backoff_cap_s: float = 60.0,
        notification_id: str = "eurevia_regate_mqtt",
        notification_title: str = "Eurevia reGATE MQTT",
        on_connected: Callable[[], None] | None = None,
        on_disconnected: Callable[[str], None] | None = None,
    ) -> None:
        self._hass = hass
        self._info = info
        self._on_message = on_message
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

        self._stop = asyncio.Event()
        self._write_lock = asyncio.Lock()

        self._task_supervisor: asyncio.Task | None = None
        self._task_rx: asyncio.Task | None = None
        self._task_ping: asyncio.Task | None = None

        self._pkt_id = 1

        # subscriptions to re-apply after reconnect (clean session)
        self._subs: set[str] = set()

        # restart policy — None = infinite retries
        self._restart_max_attempts = restart_max_attempts
        self._restart_backoff_s = max(0.0, float(restart_backoff_s))
        self._restart_backoff_cap_s = max(1.0, float(restart_backoff_cap_s))
        self._notification_id = notification_id
        self._notification_title = notification_title
        self._had_successful_connection = False
        self._disconnect_notified = False

    @property
    def is_connected(self) -> bool:
        return self._writer is not None

    async def start(self) -> None:
        """Start supervisor loop (connect + maintain)."""
        if self._task_supervisor and not self._task_supervisor.done():
            return
        self._stop.clear()
        self._task_supervisor = asyncio.create_task(
            self._supervisor_loop(), name="regate_mqtt_supervisor"
        )

    async def stop(self) -> None:
        """Stop everything and close socket."""
        self._stop.set()

        current = asyncio.current_task()

        # cancel loops (but don't cancel ourselves)
        for t in (self._task_rx, self._task_ping, self._task_supervisor):
            if t and not t.done() and t is not current:
                t.cancel()

        await self._close_transport()

        # drop references
        self._task_rx = None
        self._task_ping = None
        if self._task_supervisor is not current:
            self._task_supervisor = None

    async def subscribe(self, topic_filter: str) -> None:
        """Subscribe QoS0. If not connected, remember and apply on reconnect."""
        topic_filter = (topic_filter or "").strip()
        if not topic_filter:
            return
        self._subs.add(topic_filter)
        if self._writer is None:
            return
        await self._send_subscribe(topic_filter)

    async def publish(self, topic: str, payload: bytes) -> None:
        """Publish QoS0."""
        topic = (topic or "").strip()
        if not topic:
            return
        if self._writer is None:
            raise RuntimeError("MQTT writer not ready (disconnected)")

        varhdr = _pack_str(topic)
        fixed = bytes([0x30]) + _enc_varint(len(varhdr) + len(payload))
        await self._write(fixed + varhdr + payload)

    # ---------------- internal ----------------

    async def _supervisor_loop(self) -> None:
        attempts = 0
        last_exc: Exception | None = None

        while not self._stop.is_set():
            try:
                await self._connect_once()
                attempts = 0
                last_exc = None
                if not self._had_successful_connection:
                    self._had_successful_connection = True
                    self._disconnect_notified = False
                    self._call_connected()
                elif self._disconnect_notified:
                    self._disconnect_notified = False
                    self._call_connected()

                # Re-apply subscriptions after reconnect
                for tf in sorted(self._subs):
                    try:
                        await self._send_subscribe(tf)
                    except Exception:
                        _LOGGER.debug("Failed to resubscribe to %s", tf, exc_info=True)

                await self._wait_for_disconnect()

            except asyncio.CancelledError:
                return
            except Exception as e:
                last_exc = e
                attempts += 1
                _LOGGER.warning(
                    "MQTT supervisor error (attempt %s): %s",
                    attempts,
                    e,
                )

                await self._close_transport()

                if self._had_successful_connection and not self._disconnect_notified:
                    self._disconnect_notified = True
                    self._call_disconnected(repr(last_exc))

                if self._restart_max_attempts is not None and attempts > self._restart_max_attempts:
                    msg = f"MQTT connection failed during setup. Last error: {repr(last_exc)}"
                    _LOGGER.error(msg)
                    self._notify_ha(msg)
                    self._stop.set()
                    await self._close_transport()
                    return

                backoff = self._restart_backoff_s * (2 ** (attempts - 1))
                backoff = min(backoff, self._restart_backoff_cap_s)
                if backoff > 0:
                    await asyncio.sleep(backoff)

    def _call_connected(self) -> None:
        if self._on_connected is None:
            return
        try:
            self._on_connected()
        except Exception:
            _LOGGER.debug("on_connected callback failed", exc_info=True)

    def _call_disconnected(self, reason: str) -> None:
        if self._on_disconnected is None:
            return
        try:
            self._on_disconnected(reason)
        except Exception:
            _LOGGER.debug("on_disconnected callback failed", exc_info=True)

    async def _connect_once(self) -> None:
        await self._close_transport()

        self._reader, self._writer = await asyncio.open_connection(self._info.host, self._info.port)
        await self._send_connect()
        await self._read_connack()

        self._task_rx = asyncio.create_task(self._rx_loop(), name="regate_mqtt_rx")
        self._task_ping = asyncio.create_task(self._ping_loop(), name="regate_mqtt_ping")

        _LOGGER.info(
            "MQTT connected to %s:%s (client_id=%s)",
            self._info.host,
            self._info.port,
            self._info.client_id,
        )

    async def _wait_for_disconnect(self) -> None:
        tasks = [t for t in (self._task_rx, self._task_ping) if t is not None]
        if not tasks:
            return

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()

        # If a task ended with an exception, bubble it to supervisor
        for t in done:
            if t.cancelled():
                continue
            exc = t.exception()
            if exc:
                raise exc

        # Normal completion => treat as disconnect
        raise ConnectionError("MQTT loop ended (disconnect)")

    async def _close_transport(self) -> None:
        # cancel loops
        for t in (self._task_rx, self._task_ping):
            if t and not t.done():
                t.cancel()

        self._task_rx = None
        self._task_ping = None

        # close socket
        try:
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
        except Exception:
            pass

        self._reader = None
        self._writer = None

    async def _write(self, data: bytes) -> None:
        if not self._writer:
            raise RuntimeError("MQTT writer not ready")
        async with self._write_lock:
            self._writer.write(data)
            await self._writer.drain()

    def _next_id(self) -> int:
        pid = self._pkt_id
        self._pkt_id = 1 if self._pkt_id >= 0xFFFF else self._pkt_id + 1
        return pid

    async def _send_connect(self) -> None:
        proto_name = _pack_str("MQTT")
        proto_level = bytes([4])
        connect_flags = bytes([0x02])  # clean session
        keepalive = int(self._info.keepalive).to_bytes(2, "big")
        varhdr = proto_name + proto_level + connect_flags + keepalive
        payload = _pack_str(self._info.client_id)
        fixed = bytes([0x10]) + _enc_varint(len(varhdr) + len(payload))
        await self._write(fixed + varhdr + payload)

    async def _read_connack(self) -> None:
        if not self._reader:
            raise RuntimeError("MQTT reader not ready")
        hdr = await _read_exact(self._reader, 1)
        if hdr[0] != 0x20:
            raise ValueError(f"Expected CONNACK, got {hdr[0]:#x}")
        rem = await _read_varlen(self._reader)
        data = await _read_exact(self._reader, rem)
        rc = data[1] if len(data) >= 2 else 255
        if rc != 0:
            raise ConnectionError(f"CONNACK return code={rc}")

    async def _send_subscribe(self, topic_filter: str) -> None:
        if not self._writer:
            raise RuntimeError("MQTT writer not ready")
        pkt_id = self._next_id()
        payload = _pack_str(topic_filter) + bytes([0])  # QoS0
        varhdr = pkt_id.to_bytes(2, "big")
        fixed = bytes([0x82]) + _enc_varint(len(varhdr) + len(payload))
        await self._write(fixed + varhdr + payload)

    async def _ping_loop(self) -> None:
        try:
            while not self._stop.is_set():
                await asyncio.sleep(max(5, int(self._info.keepalive) - 5))
                if self._stop.is_set():
                    break
                try:
                    await self._write(b"\xc0\x00")  # PINGREQ
                except Exception as e:
                    raise ConnectionError(f"PINGREQ failed: {e}") from e
        except asyncio.CancelledError:
            return

    async def _rx_loop(self) -> None:
        """
        RX loop must be the ONLY reader.
        Handles PUBLISH and ignores others (SUBACK, PINGRESP, etc.).
        """
        try:
            if not self._reader:
                return

            while not self._stop.is_set():
                try:
                    b1 = await self._reader.readexactly(1)
                except asyncio.IncompleteReadError as e:
                    raise ConnectionError("Socket closed") from e

                ptype = b1[0] >> 4
                flags = b1[0] & 0x0F
                rem_len = await _read_varlen(self._reader)
                body = await _read_exact(self._reader, rem_len)

                # PUBLISH = 3
                if ptype == 3:
                    if rem_len < 2:
                        continue
                    tlen = int.from_bytes(body[0:2], "big")
                    idx = 2
                    if idx + tlen > len(body):
                        continue

                    topic = body[idx : idx + tlen].decode("utf-8", errors="ignore")
                    idx += tlen

                    qos = (flags & 0b0110) >> 1
                    if qos != 0 and idx + 2 <= len(body):
                        idx += 2  # skip packet id (qos1/2 not supported)

                    payload = body[idx:]

                    # IMPORTANT: don't let parsing crash trigger reconnect loops
                    try:
                        await self._on_message(topic, payload)
                    except Exception:
                        _LOGGER.exception("on_message crashed for topic=%s", topic)
                        continue

                else:
                    # ignore CONNACK(2), SUBACK(9), PINGRESP(13), etc.
                    continue

        except asyncio.CancelledError:
            return
        except Exception as e:
            raise ConnectionError(f"RX loop crashed: {e}") from e

    def _notify_ha(self, message: str) -> None:
        configure_url = "/config/integrations/integration/eurevia_regate_rsmart"
        body = f"{message}\n\n[Open integration settings]({configure_url})"

        def _create() -> None:
            persistent_notification.create(
                self._hass,
                body,
                title=self._notification_title,
                notification_id=self._notification_id,
            )

        self._hass.loop.call_soon_threadsafe(_create)

    def dismiss_notification(self) -> None:
        def _dismiss() -> None:
            persistent_notification.dismiss(self._hass, self._notification_id)

        self._hass.loop.call_soon_threadsafe(_dismiss)
