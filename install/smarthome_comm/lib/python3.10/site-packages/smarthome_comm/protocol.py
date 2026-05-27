from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
from typing import Dict, List, Optional, Tuple

from .crc import crc16_modbus


MAGIC = b"\xA5\x5A"
VERSION = 1
HEADER_FMT = "<2sBBHH"  # magic, version, seq, cmd_id, payload_len
HEADER_SIZE = struct.calcsize(HEADER_FMT)
CRC_SIZE = 2
MAX_PAYLOAD = 512


class CmdId(IntEnum):
    # 上位机 -> 下位机
    HEARTBEAT_TX = 0x0001
    CHASSIS_VEL = 0x0101
    VISION_TARGET = 0x0201
    GRIPPER = 0x0301
    ARM_COMMAND = 0x0302
    ESTOP = 0x0401
    NAV_EVENT = 0x0501

    # 下位机 -> 上位机
    HEARTBEAT_RX = 0x8001
    LOWER_STATE = 0x8002
    ARM_STATUS = 0x8003
    ACK = 0x80FF


CMD_NAMES: Dict[int, str] = {int(v): v.name for v in CmdId}


@dataclass
class Frame:
    cmd_id: int
    seq: int
    payload: bytes
    crc_ok: bool = True

    @property
    def name(self) -> str:
        return CMD_NAMES.get(int(self.cmd_id), f"UNKNOWN_0x{int(self.cmd_id):04X}")


def pack_frame(cmd_id: int, seq: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload too large: {len(payload)} > {MAX_PAYLOAD}")
    header = struct.pack(HEADER_FMT, MAGIC, VERSION, seq & 0xFF, int(cmd_id) & 0xFFFF, len(payload))
    crc = crc16_modbus(header + payload)
    return header + payload + struct.pack("<H", crc)


class FrameParser:
    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> List[Frame]:
        if data:
            self._buf.extend(data)
        frames: List[Frame] = []

        while True:
            magic_index = self._buf.find(MAGIC)
            if magic_index < 0:
                if len(self._buf) > 2:
                    del self._buf[:-1]
                break
            if magic_index > 0:
                del self._buf[:magic_index]

            if len(self._buf) < HEADER_SIZE:
                break

            magic, version, seq, cmd_id, payload_len = struct.unpack(
                HEADER_FMT, bytes(self._buf[:HEADER_SIZE])
            )
            if magic != MAGIC or version != VERSION or payload_len > MAX_PAYLOAD:
                del self._buf[0]
                continue

            total_len = HEADER_SIZE + payload_len + CRC_SIZE
            if len(self._buf) < total_len:
                break

            raw = bytes(self._buf[:total_len])
            payload = raw[HEADER_SIZE:HEADER_SIZE + payload_len]
            got_crc = struct.unpack("<H", raw[-2:])[0]
            calc_crc = crc16_modbus(raw[:-2])
            frames.append(Frame(cmd_id=cmd_id, seq=seq, payload=payload, crc_ok=(got_crc == calc_crc)))
            del self._buf[:total_len]

        return frames


def pack_chassis_vel(vx: float, vy: float, wz: float) -> bytes:
    """vx, vy in m/s, wz in rad/s."""
    return struct.pack("<fff", float(vx), float(vy), float(wz))


def pack_object_target(class_id: int, source: int, x: float, y: float, z: float, score: float) -> bytes:
    """Vision target payload.

    class_id: 0 meat / 1 vegetable / 2 fruit / 3 other or user-defined.
    source: 0 object / 1 QR / 2 manual.
    x,y,z: target position in the declared frame, meters.
    score: confidence in [0,1].
    """
    return struct.pack("<BBffff", int(class_id) & 0xFF, int(source) & 0xFF, float(x), float(y), float(z), float(score))


def pack_gripper(open_gripper: bool) -> bytes:
    return struct.pack("<B", 1 if open_gripper else 0)


def pack_estop(enable_estop: bool) -> bytes:
    return struct.pack("<B", 1 if enable_estop else 0)


def pack_arm_command(command: int, class_id: int, position: Tuple[float, float, float], quat_xyzw: Tuple[float, float, float, float]) -> bytes:
    return struct.pack(
        "<BBfffffff",
        int(command) & 0xFF,
        int(class_id) & 0xFF,
        float(position[0]), float(position[1]), float(position[2]),
        float(quat_xyzw[0]), float(quat_xyzw[1]), float(quat_xyzw[2]), float(quat_xyzw[3]),
    )


def pack_nav_event(event_code: int, zone_id: int) -> bytes:
    return struct.pack("<BB", int(event_code) & 0xFF, int(zone_id) & 0xFF)


def unpack_lower_state(payload: bytes) -> Optional[dict]:
    """Parse LOWER_STATE payload.

    Layout: uint8 mode, uint8 estop, float battery_v, float battery_i,
            float chassis_temp, uint16 error_code, uint32 uptime_ms.
    """
    fmt = "<BBfffHI"
    size = struct.calcsize(fmt)
    if len(payload) < size:
        return None
    mode, estop, battery_v, battery_i, temp, error, uptime_ms = struct.unpack(fmt, payload[:size])
    return {
        "mode": mode,
        "estop": bool(estop),
        "battery_voltage": battery_v,
        "battery_current": battery_i,
        "chassis_temp": temp,
        "error_code": error,
        "uptime_ms": uptime_ms,
    }


def unpack_ack(payload: bytes) -> Optional[dict]:
    fmt = "<HBB"
    if len(payload) < struct.calcsize(fmt):
        return None
    ack_cmd, ok, reason = struct.unpack(fmt, payload[:struct.calcsize(fmt)])
    return {"ack_cmd": ack_cmd, "ok": bool(ok), "reason": reason}
