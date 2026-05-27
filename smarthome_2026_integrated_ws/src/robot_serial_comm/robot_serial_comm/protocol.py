from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct
from typing import List, Optional

from .crc import crc16_modbus


VISION_TO_GIMBAL_HEAD = b"SP"
GIMBAL_TO_VISION_HEAD = b"VS"

VISION_TO_GIMBAL_BODY_FMT = "<2sBbBffffff"
VISION_TO_GIMBAL_FMT = VISION_TO_GIMBAL_BODY_FMT + "H"
GIMBAL_TO_VISION_BODY_FMT = "<2sB"
GIMBAL_TO_VISION_FMT = GIMBAL_TO_VISION_BODY_FMT + "H"

VISION_TO_GIMBAL_SIZE = struct.calcsize(VISION_TO_GIMBAL_FMT)
GIMBAL_TO_VISION_SIZE = struct.calcsize(GIMBAL_TO_VISION_FMT)


class VisionMode(IntEnum):
    IDLE = 0
    DETECT_OBJECT = 1
    DETECT_QR = 2


@dataclass
class VisionToGimbal:
    command: int = 0
    class_id: int = -1
    zone_id: int = 0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    wz: float = 0.0

    def pack(self) -> bytes:
        body = struct.pack(
            VISION_TO_GIMBAL_BODY_FMT,
            VISION_TO_GIMBAL_HEAD,
            _u8(self.command),
            _i8(self.class_id),
            _u8(self.zone_id),
            float(self.x),
            float(self.y),
            float(self.z),
            float(self.vx),
            float(self.vy),
            float(self.wz),
        )
        return body + struct.pack("<H", crc16_modbus(body))


@dataclass
class GimbalToVision:
    mode: int
    crc_ok: bool = True


def bytes_to_hex(data: bytes) -> str:
    return " ".join(f"{value:02X}" for value in data)


def unpack_gimbal_to_vision(packet: bytes) -> Optional[GimbalToVision]:
    if len(packet) != GIMBAL_TO_VISION_SIZE:
        return None
    head, mode, got_crc = struct.unpack(GIMBAL_TO_VISION_FMT, packet)
    if head != GIMBAL_TO_VISION_HEAD:
        return None
    calc_crc = crc16_modbus(packet[:-2])
    return GimbalToVision(mode=int(mode), crc_ok=(calc_crc == got_crc))


class GimbalToVisionParser:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> List[GimbalToVision]:
        if data:
            self._buffer.extend(data)

        frames: List[GimbalToVision] = []
        while len(self._buffer) >= GIMBAL_TO_VISION_SIZE:
            head_index = self._buffer.find(GIMBAL_TO_VISION_HEAD)
            if head_index < 0:
                del self._buffer[:-1]
                break
            if head_index > 0:
                del self._buffer[:head_index]
            if len(self._buffer) < GIMBAL_TO_VISION_SIZE:
                break

            raw = bytes(self._buffer[:GIMBAL_TO_VISION_SIZE])
            frame = unpack_gimbal_to_vision(raw)
            if frame is None:
                del self._buffer[0]
                continue

            frames.append(frame)
            del self._buffer[:GIMBAL_TO_VISION_SIZE]

        return frames


def _u8(value: int) -> int:
    return max(0, min(255, int(value)))


def _i8(value: int) -> int:
    return max(-128, min(127, int(value)))
