from __future__ import annotations

import os
from typing import Optional


class SerialTransport:
    def __init__(self, device: str, baudrate: int, timeout: float = 0.0, fake: bool = False) -> None:
        self.device = device
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        self.fake = bool(fake)
        self._serial = None

    def open(self) -> None:
        if self.fake:
            return
        if not self.device:
            raise RuntimeError("serial_device is empty while fake_mode is false")
        import serial  # lazy import, so fake mode does not require pyserial at runtime
        self._serial = serial.Serial(self.device, self.baudrate, timeout=self.timeout)

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def read_available(self) -> bytes:
        if self.fake or self._serial is None:
            return b""
        n = getattr(self._serial, "in_waiting", 0)
        if n <= 0:
            return b""
        return self._serial.read(n)

    def write(self, data: bytes) -> int:
        if self.fake:
            return len(data)
        if self._serial is None:
            raise RuntimeError("serial port is not open")
        return int(self._serial.write(data))

    @property
    def is_open(self) -> bool:
        return self.fake or self._serial is not None
