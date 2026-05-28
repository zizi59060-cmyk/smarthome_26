from __future__ import annotations


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
        if self.is_open:
            return
        if not self.device:
            raise RuntimeError("serial_device is empty while fake_mode is false")
        import serial

        self.close()
        self._serial = serial.Serial(self.device, self.baudrate, timeout=self.timeout)

    def close(self) -> None:
        serial_obj = self._serial
        self._serial = None
        if serial_obj is not None:
            try:
                serial_obj.close()
            except Exception:
                pass

    def reopen(self) -> None:
        self.close()
        self.open()

    def mark_disconnected(self) -> None:
        self.close()

    def read_available(self) -> bytes:
        if self.fake:
            return b""
        serial_obj = self._serial
        if serial_obj is None or not self.is_open:
            raise RuntimeError("serial port is not open")
        try:
            waiting = int(getattr(serial_obj, "in_waiting", 0))
            if waiting <= 0:
                return b""
            return bytes(serial_obj.read(waiting))
        except Exception:
            self.mark_disconnected()
            raise

    def write(self, data: bytes) -> int:
        if self.fake:
            return len(data)
        serial_obj = self._serial
        if serial_obj is None or not self.is_open:
            raise RuntimeError("serial port is not open")
        try:
            return int(serial_obj.write(data))
        except Exception:
            self.mark_disconnected()
            raise

    @property
    def is_open(self) -> bool:
        if self.fake:
            return True
        if self._serial is None:
            return False
        return bool(getattr(self._serial, "is_open", True))
