"""Exercise the actual client read/write paths with an expiring device session."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import custom_components.pichler_pkom4_local.client as transport
from custom_components.pichler_pkom4_local.client import (
    DATAPOINTS,
    SETPOINTS,
    Pkom4Client,
    Pkom4Error,
)


def expiring_client(monkeypatch):
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(transport, "time", SimpleNamespace(monotonic=lambda: clock.now))
    client = Pkom4Client("10.42.0.20", "000000000001", "test@example.invalid")
    sessions = []

    def connect():
        client.socket = Mock()
        sessions.append(clock.now)
        client._last_activity = clock.now

    def query(command, *, allow_write=False):
        if clock.now - client._last_activity >= 30:
            raise TimeoutError("Device has expired the idle session")
        client._last_activity = clock.now
        if allow_write:
            return b"\x01"
        count = len(DATAPOINTS) if command[:4] == b"\0\0\0\x2d" else len(SETPOINTS)
        prefix = b"" if command[:4] == b"\0\0\0\x2d" else b"\0"
        return prefix + count.to_bytes(2, "big") + b"\0\x64" * count

    client._connect = Mock(side_effect=connect)
    client._query = Mock(side_effect=query)
    return client, clock, sessions


def test_poll_after_idle_returns_fresh_data_without_an_unavailable_cycle(monkeypatch):
    client, clock, sessions = expiring_client(monkeypatch)
    first = client.read()
    clock.now += 30
    assert client.read() == first
    clock.now += 30
    assert client.read() == first
    assert len(sessions) == 3
    assert client._query.call_count == 6


def test_write_renews_idle_session_before_sending_and_never_replays_command(monkeypatch):
    client, clock, sessions = expiring_client(monkeypatch)
    client.read()
    clock.now += 30
    client.write("VENTILATION", 2)
    assert len(sessions) == 2
    assert sum(call.kwargs.get("allow_write", False) for call in client._query.call_args_list) == 1


def test_transient_read_failure_reconnects_within_the_same_poll(monkeypatch):
    client, _, sessions = expiring_client(monkeypatch)
    normal = client._query.side_effect
    failed = False

    def fail_once(command, **kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise TimeoutError("Dropped UDP response")
        return normal(command, **kwargs)

    client._query.side_effect = fail_once
    assert client.read()["POWER_TOTAL"] == 30
    assert len(sessions) == 2
    assert client._query.call_count == 3


def test_persistent_failure_is_bounded_and_does_not_return_stale_data(monkeypatch):
    client, _, sessions = expiring_client(monkeypatch)
    client._query.side_effect = TimeoutError("Device offline")
    with pytest.raises(Pkom4Error, match="reading failed"):
        client.read()
    assert len(sessions) == 2
    assert client._query.call_count == 2
    assert client.socket is None


def test_recent_session_is_reused(monkeypatch):
    client, clock, sessions = expiring_client(monkeypatch)
    first = client.read()
    clock.now += 2
    assert client.read() == first
    assert len(sessions) == 1


def test_valid_reply_updates_session_activity(monkeypatch):
    from genvexnabto.protocol import GenvexPacket, GenvexPacketType, GenvexPayloadCrypt

    clock = SimpleNamespace(now=123.0)
    monkeypatch.setattr(transport, "time", SimpleNamespace(monotonic=lambda: clock.now))
    client = Pkom4Client("10.42.0.20", "000000000001", "test@example.invalid")
    client.socket = Mock()
    client.client_id = b"clnt"
    client.server_id = b"srvr"
    payload = GenvexPayloadCrypt()
    payload.setData(b"pong" + b"\x02")
    packet = GenvexPacket.build_packet(b"clnt", b"srvr", GenvexPacketType.DATA, 1, [payload])
    client._receive = Mock(return_value=packet)
    assert client._query(b"\0\0\0\x11") == b"pong"
    assert client._last_activity == 123.0
    client.close()
    assert client._last_activity is None


def test_retry_discards_partial_snapshot(monkeypatch):
    client, _, sessions = expiring_client(monkeypatch)
    normal = client._query.side_effect
    calls = 0

    def fail_second(command, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise TimeoutError("Setpoint response lost after datapoints arrived")
        reply = normal(command, **kwargs)
        if calls > 2:
            reply = reply.replace(b"\0\x64", b"\0\xc8")
        return reply

    client._query.side_effect = fail_second
    data = client.read()
    assert len(sessions) == 2
    assert data["TEMPERATURE_IST"] == 2
    assert data["HOTWATER"] == 2
    assert data["POWER_TOTAL"] == 60
