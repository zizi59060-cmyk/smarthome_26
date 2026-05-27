"""CRC16 helpers.

Default polynomial is Modbus/IBM: poly=0xA001, init=0xFFFF.
The function returns an unsigned 16-bit integer and the frame stores it little-endian.
"""

from __future__ import annotations


def crc16_modbus(data: bytes, init: int = 0xFFFF) -> int:
    crc = init & 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            crc &= 0xFFFF
    return crc & 0xFFFF
