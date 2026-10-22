"""Local PKOM4 transport using GenvexNabto Micro Nabto framing (GPL-3.0)."""

import ipaddress
import secrets
import socket
import time
from datetime import date
from decimal import Decimal, InvalidOperation
from threading import RLock

from genvexnabto.protocol import (
    GenvexCommandDatapointReadList,
    GenvexCommandPing,
    GenvexCommandSetpointReadList,
    GenvexCommandSetpointWriteList,
    GenvexDiscovery,
    GenvexPacket,
    GenvexPacketType,
    GenvexPayloadCP_ID,
    GenvexPayloadCrypt,
    GenvexPayloadIPX,
)

from .registers import REGISTERS

# Renew conservatively before the observed 30-second idle-session failure.
SESSION_IDLE_SECONDS = 15

DATAPOINTS = (
    "TEMPERATURE_IST",
    "T1_ZULUFT",
    "T3_AUSSENZULUFT",
    "T4_FORTLUFT",
    "T7_ABLUFT",
    "T21_SPEICHER_MITTE",
    "T20_SPEICHER_UNTEN",
    "LUFTMENGE_ZU",
    "LUFTMENGE_AB",
    "ENERGIEVERBRAUCH",
    "LEISTUNG_HK_KOMPR",
    "LEISTUNG_BW_KOMPR",
    "LEISTUNG_PLAT_VENT",
    "VENTILATION_IST",
    "MALFUNCTION",
    "STATUS_BITS",
)
SETPOINTS = (
    "OP_MODE",
    "VENTILATION",
    "TEMPERATURE_SOLL_NORMAL",
    "HOTWATER",
    "HOTWATER_FAST_HEATING",
    "TEMPERATURE_SOLL_ACTIVE_COOLING",
    "TEMPERATURE_IS_ACTIVE_COOLING",
    "HOTWATER_E_HEATING",
    "OP_HOLIDAY_YEAR",
    "OP_HOLIDAY_MONTH",
    "OP_HOLIDAY_DAY",
)

# Only controls exposed by PICHLERluft are writable. Service registers are excluded.
WRITABLE = {
    "OP_MODE": (Decimal("0"), Decimal("4"), Decimal("1")),
    "VENTILATION": (Decimal("0"), Decimal("4"), Decimal("1")),
    "TEMPERATURE_SOLL_NORMAL": (Decimal("10"), Decimal("30"), Decimal("0.5")),
    "HOTWATER": (Decimal("20"), Decimal("75"), Decimal("0.5")),
    "HOTWATER_FAST_HEATING": (Decimal("0"), Decimal("1"), Decimal("1")),
    "HOTWATER_E_HEATING": (Decimal("0"), Decimal("1"), Decimal("1")),
    "TEMPERATURE_SOLL_ACTIVE_COOLING": (Decimal("15"), Decimal("40"), Decimal("0.5")),
    "TEMPERATURE_IS_ACTIVE_COOLING": (Decimal("0"), Decimal("2"), Decimal("1")),
    "OP_HOLIDAY_YEAR": (Decimal("0"), Decimal("99"), Decimal("1")),
    "OP_HOLIDAY_MONTH": (Decimal("1"), Decimal("12"), Decimal("1")),
    "OP_HOLIDAY_DAY": (Decimal("1"), Decimal("31"), Decimal("1")),
}


def build_write_command(key, value):
    if key not in WRITABLE:
        raise ValueError("Unsupported control")
    if isinstance(value, bool):
        raise ValueError("Expected a numeric setpoint")
    try:
        converted = Decimal(str(value))
    except InvalidOperation as err:
        raise ValueError("Invalid setpoint") from err
    low, high, step = WRITABLE[key]
    if not converted.is_finite() or not low <= converted <= high or (converted - low) % step:
        raise ValueError("Setpoint outside allowed range or step")
    register = REGISTERS[key]
    raw = converted * (10 ** (register["Decimal"] or 0))
    if raw != raw.to_integral_value() or not 0 <= raw <= 65535:
        raise ValueError("Invalid raw setpoint")
    return GenvexCommandSetpointWriteList.buildCommand(
        [(register["W_OBJ"], register["W_ADDR"], int(raw))]
    )


class Pkom4Error(Exception):
    """No valid reading was obtained."""


def decode_list(payload, names, setpoints=False):
    offset = 1 if setpoints else 0
    if setpoints and (not payload or payload[0] != 0):
        raise Pkom4Error("Setpoint read rejected")
    if len(payload) < offset + 2 or int.from_bytes(payload[offset : offset + 2], "big") != len(
        names
    ):
        raise Pkom4Error("Response count mismatch")
    start = offset + 2
    if len(payload) != start + 2 * len(names):
        raise Pkom4Error("Response length mismatch")
    values = {}
    for i, name in enumerate(names):
        value = int.from_bytes(payload[start + 2 * i : start + 2 * i + 2], "big", signed=True)
        if name == "STATUS_BITS":
            value &= 0xFFFF
        digits = REGISTERS[name]["Decimal"] or 0
        values[name] = value / (10**digits) if digits else value
    return values


def crypt_body(packet):
    if len(packet) < 25 or packet[16:18] != b"\x36\0" or packet[20:22] != b"\0\x0a":
        raise Pkom4Error("Unsupported Micro Nabto response")
    if (
        int.from_bytes(packet[14:16], "big") != len(packet)
        or int.from_bytes(packet[18:20], "big") != len(packet) - 16
    ):
        raise Pkom4Error("Invalid packet length")
    if sum(packet[:-2]) & 0xFFFF != int.from_bytes(packet[-2:], "big"):
        raise Pkom4Error("Invalid packet checksum")
    padding = packet[-3]
    if not 1 <= padding <= 16 or len(packet) - 2 - padding < 22:
        raise Pkom4Error("Invalid packet padding")
    return packet[22 : -2 - padding]


class Pkom4Client:
    def __init__(self, host, device_id, email):
        address = ipaddress.IPv4Address(host)
        if not address.is_private or address.is_loopback or address.is_multicast:
            raise ValueError("A private LAN IPv4 address is required")
        if not device_id.isdigit() or not 1 <= len(device_id) <= 63:
            raise ValueError("Invalid Nabto device ID")
        if not email or len(email) > 254 or not email.isascii():
            raise ValueError("Invalid local account identity")
        self._lock = RLock()
        self.address = (str(address), 5570)
        self.device_id = device_id + ".remote.lscontrol.dk"
        self.email = email
        self.socket = None
        self.client_id = secrets.token_bytes(4)
        self.server_id = b"\0" * 4
        self.sequence = 0
        self._last_activity = None

    def close(self):
        with self._lock:
            if self.socket is not None:
                self.socket.close()
            self.socket = None
            self.server_id = b"\0" * 4
            self._last_activity = None

    def _ensure_session(self):
        if (
            self.socket is not None
            and self._last_activity is not None
            and time.monotonic() - self._last_activity >= SESSION_IDLE_SECONDS
        ):
            self.close()
        if self.socket is None:
            self._connect()

    def _receive(self, kind=None, sequence=None):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            self.socket.settimeout(max(0.01, deadline - time.monotonic()))
            packet, address = self.socket.recvfrom(4096)
            if address != self.address:
                continue
            if kind is None:
                return packet
            if (
                len(packet) >= 16
                and packet[:4] == self.client_id
                and packet[8:9] == kind
                and (sequence is None or int.from_bytes(packet[12:14], "big") == sequence)
            ):
                return packet
        raise Pkom4Error("Response timed out")

    def _connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.sendto(GenvexDiscovery.build_packet(self.device_id), self.address)
        discovered = self._receive()
        if (
            discovered[:4] != b"\0\x80\0\x01"
            or discovered[19:].split(b"\0", 1)[0] != self.device_id.encode()
        ):
            raise Pkom4Error("Device identity mismatch")
        identity = GenvexPayloadCP_ID()
        identity.setEmail(self.email)
        self.socket.sendto(
            GenvexPacket.build_packet(
                self.client_id,
                b"\0" * 4,
                GenvexPacketType.U_CONNECT,
                0,
                [GenvexPayloadIPX(), identity],
            ),
            self.address,
        )
        packet = self._receive(GenvexPacketType.U_CONNECT)
        if len(packet) < 28 or packet[22:24] != b"\0\x01":
            raise Pkom4Error("Local session rejected or device busy")
        self.server_id = packet[24:28]
        pong = self._query(GenvexCommandPing().buildCommand())
        if len(pong) < 12 or pong[:4] != b"pong":
            raise Pkom4Error("Device ping failed")
        if int.from_bytes(pong[8:12], "big") != 1030:
            raise Pkom4Error("Unsupported device model")

    def _query(self, command, *, allow_write=False):
        allowed = (b"\0\0\0\x11", b"\0\0\0\x2a", b"\0\0\0\x2d")
        if allow_write:
            allowed += (b"\0\0\0\x2b",)
        if command[:4] not in allowed:
            raise Pkom4Error("Only read operations are allowed")
        self.sequence = self.sequence % 65535 + 1
        payload = GenvexPayloadCrypt()
        payload.setData(command)
        self.socket.sendto(
            GenvexPacket.build_packet(
                self.client_id, self.server_id, GenvexPacketType.DATA, self.sequence, [payload]
            ),
            self.address,
        )
        packet = self._receive(GenvexPacketType.DATA, self.sequence)
        if packet[4:8] != self.server_id:
            raise Pkom4Error("Session mismatch")
        body = crypt_body(packet)
        self._last_activity = time.monotonic()
        return body

    def read(self):
        with self._lock:
            # Reads are idempotent: recover once inside this poll, never return stale data.
            for attempt in range(2):
                try:
                    return self._read_locked()
                except Pkom4Error:
                    if attempt:
                        raise

    def _read_locked(self):
        try:
            self._ensure_session()
            dp = [
                {"obj": REGISTERS[n]["R_OBJ"], "address": REGISTERS[n]["R_ADDR"]}
                for n in DATAPOINTS
            ]
            values = decode_list(
                self._query(GenvexCommandDatapointReadList.buildCommand(dp)), DATAPOINTS
            )
            sp = [
                {"read_obj": REGISTERS[n]["R_OBJ"], "read_address": REGISTERS[n]["R_ADDR"]}
                for n in SETPOINTS
            ]
            values.update(
                decode_list(
                    self._query(GenvexCommandSetpointReadList.buildCommand(sp)), SETPOINTS, True
                )
            )
            values["POWER_TOTAL"] = round(
                sum(
                    values[n]
                    for n in ("LEISTUNG_HK_KOMPR", "LEISTUNG_BW_KOMPR", "LEISTUNG_PLAT_VENT")
                ),
                1,
            )
            return values
        except (OSError, ValueError, Pkom4Error) as e:
            self.close()
            raise Pkom4Error("Local PKOM4 reading failed") from e

    def write(self, key, value):
        return self.write_many({key: value})

    def write_many(self, updates):
        # Validate the whole batch before sending any packet. No automatic write retries.
        if not updates or len(updates) > 8:
            raise ValueError("Invalid command batch")
        calendar = {"OP_HOLIDAY_YEAR", "OP_HOLIDAY_MONTH", "OP_HOLIDAY_DAY"}
        if calendar.intersection(updates):
            if not calendar.issubset(updates):
                raise ValueError("A complete holiday date is required")
            date(
                2000 + int(updates["OP_HOLIDAY_YEAR"]),
                int(updates["OP_HOLIDAY_MONTH"]),
                int(updates["OP_HOLIDAY_DAY"]),
            )
        commands = [build_write_command(key, value) for key, value in updates.items()]
        # PKOM4 processes one setpoint per RPC, as does the official app.
        with self._lock:
            try:
                self._ensure_session()
                for command in commands:
                    reply = self._query(command, allow_write=True)
                    if reply not in (b"\0", b"\x01"):
                        raise Pkom4Error("Device rejected the command")
            except (OSError, ValueError, Pkom4Error) as err:
                self.close()
                raise Pkom4Error(
                    "Command was not confirmed; check the device before retrying"
                ) from err
