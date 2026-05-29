from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import String, UInt8

from robot_serial_comm.msg import ObjectTarget

from .protocol import (
    GIMBAL_TO_VISION_SIZE,
    GimbalToVisionParser,
    VISION_TO_GIMBAL_SIZE,
    VisionMode,
    VisionToGimbal,
    bytes_to_hex,
)
from .serial_transport import SerialTransport


@dataclass
class TargetSnapshot:
    class_id: int
    score: float
    x: float
    y: float
    z: float
    stamp_sec: float


class RobotSerialCommNode(Node):
    def __init__(self) -> None:
        super().__init__("robot_serial_comm_node")

        self.declare_parameter("serial_device", "/dev/ttyACM0")
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("fake_mode", False)
        self.declare_parameter("read_hz", 200.0)
        self.declare_parameter("send_hz", 30.0)
        self.declare_parameter("mode_pub_hz", 10.0)
        self.declare_parameter("reconnect_interval_sec", 1.0)
        self.declare_parameter("reconnect_log_interval_sec", 5.0)
        self.declare_parameter("initial_connect_required", False)
        self.declare_parameter("target_timeout_sec", 0.5)
        self.declare_parameter("target_topic", "/smarthome/object_target")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("zone_id_topic", "/smarthome/zone_id")
        self.declare_parameter("mode_topic", "/vision_mode")
        self.declare_parameter("raw_tx_topic", "/robot_serial_comm/raw_tx_hex")
        self.declare_parameter("raw_rx_topic", "/robot_serial_comm/raw_rx_hex")
        self.declare_parameter("serial_state_topic", "/robot_serial_comm/serial_state")
        self.declare_parameter("manual_mode_topic", "/robot_serial_comm/manual_mode")
        self.declare_parameter("default_zone_id", 0)
        self.declare_parameter("default_mode", int(VisionMode.IDLE))
        self.declare_parameter("accept_lower_mode", True)

        self.latest_target: Optional[TargetSnapshot] = None
        self.latest_twist = Twist()
        self.zone_id = _clamp_u8(self.get_parameter("default_zone_id").value, 0, 6)
        self.current_mode = _clamp_u8(self.get_parameter("default_mode").value, 0, 2)
        self.reconnect_log_interval_sec = max(
            0.0, float(self.get_parameter("reconnect_log_interval_sec").value)
        )
        self.initial_connect_required = _as_bool(
            self.get_parameter("initial_connect_required").value
        )
        self.last_reconnect_log_sec = 0.0
        self.last_serial_state = ""
        self.last_ignored_lower_mode: Optional[int] = None

        self.parser = GimbalToVisionParser()
        self.transport = SerialTransport(
            device=str(self.get_parameter("serial_device").value),
            baudrate=int(self.get_parameter("baudrate").value),
            fake=_as_bool(self.get_parameter("fake_mode").value),
        )

        self.raw_tx_pub = self.create_publisher(String, str(self.get_parameter("raw_tx_topic").value), 10)
        self.raw_rx_pub = self.create_publisher(String, str(self.get_parameter("raw_rx_topic").value), 10)
        self.serial_state_pub = self.create_publisher(
            String, str(self.get_parameter("serial_state_topic").value), 10
        )
        self.mode_pub = self.create_publisher(UInt8, str(self.get_parameter("mode_topic").value), 10)

        mode = "FAKE" if self.transport.fake else f"{self.transport.device}@{self.transport.baudrate}"
        self.get_logger().info(f"robot serial comm started: {mode}")
        self.get_logger().info(
            f"VisionToGimbal size={VISION_TO_GIMBAL_SIZE} bytes, "
            f"GimbalToVision size={GIMBAL_TO_VISION_SIZE} bytes"
        )
        if not self.accept_lower_mode():
            self.get_logger().info(
                f"lower-computer mode input disabled; upper mode starts at {self.current_mode}"
            )
        connected = self.try_open_serial(force_log=True)
        if not connected and self.initial_connect_required:
            raise RuntimeError(
                f"failed to open serial port {self.transport.device}@{self.transport.baudrate}"
            )

        self.target_sub = self.create_subscription(
            ObjectTarget,
            str(self.get_parameter("target_topic").value),
            self.on_target,
            10,
        )
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            str(self.get_parameter("cmd_vel_topic").value),
            self.on_cmd_vel,
            10,
        )
        self.zone_sub = self.create_subscription(
            UInt8,
            str(self.get_parameter("zone_id_topic").value),
            self.on_zone_id,
            10,
        )
        self.manual_mode_sub = self.create_subscription(
            UInt8,
            str(self.get_parameter("manual_mode_topic").value),
            self.on_manual_mode,
            10,
        )

        read_period = 1.0 / max(1.0, float(self.get_parameter("read_hz").value))
        send_period = 1.0 / max(1.0, float(self.get_parameter("send_hz").value))
        mode_period = 1.0 / max(1.0, float(self.get_parameter("mode_pub_hz").value))
        reconnect_period = max(0.1, float(self.get_parameter("reconnect_interval_sec").value))
        self.read_timer = self.create_timer(read_period, self.read_serial_once)
        self.send_timer = self.create_timer(send_period, self.send_packet_once)
        self.mode_timer = self.create_timer(mode_period, self.publish_mode_once)
        self.reconnect_timer = self.create_timer(reconnect_period, self.reconnect_serial_once)

    def destroy_node(self) -> bool:
        self.transport.close()
        return super().destroy_node()

    def now_sec(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def accept_lower_mode(self) -> bool:
        return _as_bool(self.get_parameter("accept_lower_mode").value)

    def publish_serial_state(self, state: str, force: bool = False) -> None:
        if not force and state == self.last_serial_state:
            return
        self.last_serial_state = state
        msg = String()
        msg.data = state
        self.serial_state_pub.publish(msg)

    def try_open_serial(self, force_log: bool = False) -> bool:
        if self.transport.fake:
            self.publish_serial_state("fake", force=force_log)
            return True
        if self.transport.is_open:
            self.publish_serial_state("connected", force=force_log)
            return True

        try:
            self.transport.open()
        except Exception as exc:
            self.publish_serial_state("disconnected", force=force_log)
            now = self.now_sec()
            should_log = force_log or (
                self.reconnect_log_interval_sec <= 0.0
                or now - self.last_reconnect_log_sec >= self.reconnect_log_interval_sec
            )
            if should_log:
                self.last_reconnect_log_sec = now
                self.get_logger().warn(
                    f"serial disconnected, reconnecting every "
                    f"{float(self.get_parameter('reconnect_interval_sec').value):.2f}s: {exc}"
                )
            return False

        self.parser = GimbalToVisionParser()
        self.publish_serial_state("connected", force=True)
        self.get_logger().info(
            f"serial connected: {self.transport.device}@{self.transport.baudrate}"
        )
        return True

    def reconnect_serial_once(self) -> None:
        if self.transport.is_open:
            state = "fake" if self.transport.fake else "connected"
            self.publish_serial_state(state, force=True)
            return
        self.try_open_serial()

    def handle_serial_error(self, operation: str, exc: Exception) -> None:
        if self.transport.fake:
            return
        self.transport.mark_disconnected()
        self.publish_serial_state("disconnected", force=True)
        self.get_logger().warn(f"serial {operation} failed, will reconnect: {exc}")

    def on_target(self, msg: ObjectTarget) -> None:
        pos = msg.pose.pose.position
        stamp = msg.stamp.sec + msg.stamp.nanosec * 1e-9
        if stamp <= 0.0:
            stamp = self.now_sec()
        self.latest_target = TargetSnapshot(
            class_id=int(msg.class_id),
            score=float(msg.score),
            x=float(pos.x),
            y=float(pos.y),
            z=float(pos.z),
            stamp_sec=stamp,
        )

    def on_cmd_vel(self, msg: Twist) -> None:
        self.latest_twist = msg

    def on_zone_id(self, msg: UInt8) -> None:
        self.zone_id = _clamp_u8(msg.data, 0, 6)

    def on_manual_mode(self, msg: UInt8) -> None:
        if msg.data not in (int(VisionMode.IDLE), int(VisionMode.DETECT_OBJECT), int(VisionMode.DETECT_QR)):
            self.get_logger().warn(f"invalid upper-computer manual vision mode: {msg.data}")
            return
        if int(msg.data) != self.current_mode:
            self.get_logger().info(f"upper vision mode changed: {self.current_mode} -> {msg.data}")
        self.current_mode = int(msg.data)
        self.publish_mode_once()

    def build_packet(self) -> VisionToGimbal:
        target = self.latest_target
        target_fresh = False
        if target is not None:
            target_fresh = self.now_sec() - target.stamp_sec <= float(
                self.get_parameter("target_timeout_sec").value
            )

        has_target = bool(target_fresh and target is not None and target.class_id >= 0)
        twist = self.latest_twist
        return VisionToGimbal(
            command=1 if has_target else 0,
            class_id=target.class_id if has_target and target is not None else -1,
            zone_id=self.zone_id,
            x=target.x if has_target and target is not None else 0.0,
            y=target.y if has_target and target is not None else 0.0,
            z=target.z if has_target and target is not None else 0.0,
            vx=float(twist.linear.x),
            vy=float(twist.linear.y),
            wz=float(twist.angular.z),
        )

    def send_packet_once(self) -> None:
        if not self.transport.is_open:
            return
        packet = self.build_packet()
        raw = packet.pack()
        try:
            self.transport.write(raw)
        except Exception as exc:
            self.handle_serial_error("write", exc)
            return

        msg = String()
        msg.data = bytes_to_hex(raw)
        self.raw_tx_pub.publish(msg)

    def read_serial_once(self) -> None:
        if not self.transport.is_open:
            return
        try:
            data = self.transport.read_available()
        except Exception as exc:
            self.handle_serial_error("read", exc)
            return
        if not data:
            return

        rx = String()
        rx.data = bytes_to_hex(data)
        self.raw_rx_pub.publish(rx)

        for frame in self.parser.feed(data):
            if not frame.crc_ok:
                self.get_logger().warn("GimbalToVision CRC mismatch")
                continue
            if frame.mode not in (int(VisionMode.IDLE), int(VisionMode.DETECT_OBJECT), int(VisionMode.DETECT_QR)):
                self.get_logger().warn(f"unknown vision mode from lower computer: {frame.mode}")
                continue
            if not self.accept_lower_mode():
                if self.last_ignored_lower_mode != frame.mode:
                    self.get_logger().info(
                        f"ignored lower-computer vision mode {frame.mode}; "
                        f"upper mode remains {self.current_mode}"
                    )
                    self.last_ignored_lower_mode = frame.mode
                continue
            if frame.mode != self.current_mode:
                self.get_logger().info(f"vision mode changed: {self.current_mode} -> {frame.mode}")
            self.current_mode = int(frame.mode)
            self.publish_mode_once()

    def publish_mode_once(self) -> None:
        msg = UInt8()
        msg.data = int(self.current_mode)
        self.mode_pub.publish(msg)


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _clamp_u8(value, min_value: int = 0, max_value: int = 255) -> int:
    try:
        raw = int(value)
    except (TypeError, ValueError):
        raw = min_value
    return max(min_value, min(max_value, raw))


def main(args=None) -> None:
    rclpy.init(args=args)
    node = None
    try:
        node = RobotSerialCommNode()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
