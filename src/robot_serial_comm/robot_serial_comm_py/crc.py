from __future__ import annotations


def crc16_modbus(data: bytes, init: int = 0xFFFF) -> int:
    crc = init & 0xFFFF
    for value in data:
        crc ^= int(value) & 0xFF
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            crc &= 0xFFFF
    return crc & 0xFFFF
