"""Synthetic fixtures only. These tests never open a network socket."""

from decimal import Decimal
from unittest.mock import Mock

import pytest
from genvexnabto.protocol import GenvexPacket, GenvexPacketType, GenvexPayloadCrypt

from custom_components.pichler_pkom4_local.client import (
    Pkom4Client,
    Pkom4Error,
    build_write_command,
    crypt_body,
    decode_list,
)


@pytest.mark.parametrize(
    "key,value,address,raw",
    [
        ("VENTILATION", 0, 102, 0),
        ("VENTILATION", 4, 102, 4),
        ("OP_MODE", 3, 10, 3),
        ("TEMPERATURE_SOLL_NORMAL", 21.5, 30, 2150),
        ("HOTWATER", 49, 268, 4900),
        ("HOTWATER_FAST_HEATING", 1, 222, 1),
    ],
)
def test_write_packet_matches_declared_rpc_43(key, value, address, raw):
    expected = b"\0\0\0\x2b\0\x01\0" + address.to_bytes(4, "big") + raw.to_bytes(2, "big") + b"\x01"
    assert build_write_command(key, value) == expected


@pytest.mark.parametrize(
    "key,value",
    [
        ("OP_MODE", 5),
        ("OP_MODE", 9),
        ("VENTILATION", 5),
        ("VENTILATION", -1),
        ("TEMPERATURE_SOLL_NORMAL", 31),
        ("TEMPERATURE_SOLL_NORMAL", 21.25),
        ("HOTWATER", 76),
        ("HOTWATER", float("nan")),
        ("HOTWATER", float("inf")),
        ("HOTWATER_FAST_HEATING", 2),
        ("FILTERWECHSEL", 0),
        ("MALFUNCTION", 0),
        ("OP_MODE", True),
    ],
)
def test_unsupported_controls_and_values_never_reach_transport(key, value):
    client = Pkom4Client("10.42.0.20", "000000000001", "test@example.invalid")
    client._connect = Mock()
    with pytest.raises(ValueError):
        client.write(key, value)
    client._connect.assert_not_called()


def response_packet(body):
    # Synthetic response with valid Micro Nabto padding and checksum.
    payload = GenvexPayloadCrypt()
    payload.setData(body + b"\x02")
    return GenvexPacket.build_packet(b"clnt", b"srvr", GenvexPacketType.DATA, 1, [payload])


def test_checksum_framing_and_signed_temperature():
    body = b"\0\x02" + (2150).to_bytes(2, "big") + (-425).to_bytes(2, "big", signed=True)
    packet = response_packet(body)
    assert crypt_body(packet) == body
    assert decode_list(body, ["TEMPERATURE_IST", "T3_AUSSENZULUFT"]) == {
        "TEMPERATURE_IST": 21.5,
        "T3_AUSSENZULUFT": -4.25,
    }
    damaged = bytearray(packet)
    damaged[23] ^= 1
    with pytest.raises(Pkom4Error):
        crypt_body(damaged)
    with pytest.raises(Pkom4Error):
        decode_list(body, ["TEMPERATURE_IST"])
    with pytest.raises(Pkom4Error):
        decode_list(b"\x01\0\0", [], True)


def test_status_word_is_unsigned():
    assert decode_list(b"\0\x01\x80\x01", ["STATUS_BITS"])["STATUS_BITS"] == 32769


def test_write_ack_no_retry_and_no_optimistic_state():
    client = Pkom4Client("10.42.0.20", "000000000001", "test@example.invalid")
    client.socket = Mock()
    client._query = Mock(return_value=b"\0")
    client.write("HOTWATER", Decimal("49.5"))
    client._query.assert_called_once_with(build_write_command("HOTWATER", 49.5), allow_write=True)
    client._query = Mock(side_effect=TimeoutError())
    with pytest.raises(Pkom4Error, match="not confirmed"):
        client.write("VENTILATION", 2)
    assert client._query.call_count == 1
    assert client.socket is None


def test_default_query_path_cannot_send_a_write():
    client = Pkom4Client("10.42.0.20", "000000000001", "test@example.invalid")
    with pytest.raises(Pkom4Error):
        client._query(build_write_command("VENTILATION", 2))


@pytest.mark.parametrize("host", ["8.8.8.8", "127.0.0.1", "224.0.0.1"])
def test_only_lan_addresses_are_accepted(host):
    with pytest.raises(ValueError):
        Pkom4Client(host, "000000000001", "test@example.invalid")


@pytest.mark.parametrize("ack", [b"\0", b"\x01"])
def test_both_official_app_success_statuses_are_accepted(ack):
    client = Pkom4Client("10.42.0.20", "000000000001", "test@example.invalid")
    client.socket = Mock()
    client._query = Mock(return_value=ack)
    client.write("VENTILATION", 2)
    assert client._query.call_count == 1


def test_holiday_batch_sends_one_rpc_per_register():
    client = Pkom4Client("10.42.0.20", "000000000001", "test@example.invalid")
    client.socket = Mock()
    client._query = Mock(return_value=b"\x01")
    values = {"OP_HOLIDAY_YEAR": 30, "OP_HOLIDAY_MONTH": 6, "OP_HOLIDAY_DAY": 15}
    client.write_many(values)
    assert client._query.call_count == 3
    for (key, value), call in zip(values.items(), client._query.call_args_list):
        assert call.args == (build_write_command(key, value),)
        assert call.kwargs == {"allow_write": True}
    client._query.reset_mock()
    with pytest.raises(ValueError):
        client.write_many({"OP_HOLIDAY_YEAR": 30})
    with pytest.raises(ValueError):
        client.write_many({"OP_HOLIDAY_YEAR": 30, "OP_HOLIDAY_MONTH": 2, "OP_HOLIDAY_DAY": 30})
    client._query.assert_not_called()
